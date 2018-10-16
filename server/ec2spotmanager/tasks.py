import json
import logging
import fasteners
import redis
from django.conf import settings
from django.utils import timezone
from laniakea.core.userdata import UserData
from celeryconf import app
from . import cron  # noqa ensure cron tasks get registered
from .common.prices import get_price_median
from .CloudProvider.CloudProvider import INSTANCE_STATE, PROVIDERS, CloudProvider, CloudProviderError


logger = logging.getLogger("ec2spotmanager")


SPOTMGR_TAG = "SpotManager"


@app.task
def check_instance_pool(pool_id):
    from .models import Instance, InstancePool, PoolStatusEntry, POOL_STATUS_ENTRY_TYPE

    lock = fasteners.InterProcessLock('/tmp/ec2spotmanager.pool%d.lck' % pool_id)

    instance_pool = InstancePool.objects.get(pk=pool_id)

    if not lock.acquire(blocking=False):
        logger.warning('[Pool %d] Another check still in progress, exiting.', pool_id)
        return

    try:
        criticalPoolStatusEntries = PoolStatusEntry.objects.filter(pool=instance_pool, isCritical=True)

        if criticalPoolStatusEntries:
            return

        if instance_pool.config.isCyclic() or instance_pool.config.getMissingParameters():
            entry = PoolStatusEntry()
            entry.pool = instance_pool
            entry.isCritical = True
            entry.type = POOL_STATUS_ENTRY_TYPE['config-error']
            entry.msg = "Configuration error."
            entry.save()
            return

        config = instance_pool.config.flatten()

        instance_cores_missing = config.size
        running_instances = []

        _update_pool_instances(instance_pool, config)

        instances = Instance.objects.filter(pool=instance_pool)

        for instance in instances:
            if instance.status_code in [INSTANCE_STATE['running'], INSTANCE_STATE['pending'],
                                        INSTANCE_STATE['requested']]:
                instance_cores_missing -= instance.size
                running_instances.append(instance)
            elif instance.status_code in [INSTANCE_STATE['shutting-down'], INSTANCE_STATE['terminated']]:
                # The instance is no longer running, delete it from our database
                logger.info("[Pool %d] Deleting terminated instance with ID %s from our database.",
                            instance_pool.id, instance.instance_id)
                instance.delete()
            else:

                instance_cores_missing -= instance.size
                running_instances.append(instance)

        # Continue working with the instances we have running
        instances = running_instances

        if not instance_pool.isEnabled:
            if running_instances:
                _terminate_pool_instances(running_instances, instance_pool)
                logger.info("[Pool %d] Termination complete.", instance_pool.id)

            return

        if ((not instance_pool.last_cycled) or
                instance_pool.last_cycled < timezone.now() - timezone.timedelta(seconds=config.cycle_interval)):
            logger.info("[Pool %d] Needs to be cycled, terminating all instances...", instance_pool.id)
            instance_pool.last_cycled = timezone.now()
            _terminate_pool_instances(instances, instance_pool)
            instance_pool.save()

            logger.info("[Pool %d] Termination complete.", instance_pool.id)

        if instance_cores_missing > 0:
            logger.info("[Pool %d] Needs %s more instance cores, starting...",
                        instance_pool.id, instance_cores_missing)
            _start_pool_instances(instance_pool, config, count=instance_cores_missing)
        elif instance_cores_missing < 0:
            # Select the oldest instances we have running and terminate
            # them so we meet the size limitation again.
            instances = []
            for instance in Instance.objects.filter(pool=instance_pool).order_by('created'):
                if instance_cores_missing + instance.size > 0:
                    # If this instance would leave us short of cores, let it run. Otherwise
                    # the pool size may oscillate.
                    continue
                instances.append(instance)
                instance_cores_missing += instance.size
                if instance_cores_missing == 0:
                    break
            if instances:
                instance_cores_missing = sum(instance.size for instance in instances)
                logger.info("[Pool %d] Has %d instance cores over limit in %d instances, terminating...",
                            instance_pool.id, instance_cores_missing, len(instances))
                _terminate_pool_instances(instance_pool, instances)
        else:
            logger.debug("[Pool %d] Size is ok.", instance_pool.id)

    except CloudProviderError as err:
        _update_pool_status(instance_pool, err.TYPE, err.message)
    except Exception as msg:
        _update_pool_status(instance_pool, 'unclassified', str(msg))

    finally:
        lock.release()


def _determine_best_location(config, count):
    cache = redis.StrictRedis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.REDIS_DB)

    best_zone = None
    best_region = None
    best_type = None
    best_median = None
    rejected_prices = {}

    cloud_provider = CloudProvider.get_instance(PROVIDERS[0])  # TODO: support multiple providers
    cores_per_instance = cloud_provider.get_cores_per_instance()

    # Filter machine sizes that would put us over the number of cores required. If all do, then choose the smallest.
    smallest = []
    smallest_size = None
    acceptable_types = []
    for instance_type in cloud_provider.get_instance_types(config):
        instance_size = cores_per_instance[instance_type]
        if instance_size <= count:
            acceptable_types.append(instance_type)
        # keep track of all instance types with the least number of cores for this config
        if not smallest or instance_size < smallest_size:
            smallest_size = instance_size
            smallest = [instance_type]
        elif instance_size == smallest_size:
            smallest.append(instance_type)
    # replace the allowed instance types with those that are <= count, or the smallest if none are
    instance_types = acceptable_types or smallest

    # Calculate median values for all availability zones and best zone/price
    allowed_regions = set(cloud_provider.get_allowed_regions(config))
    for instance_type in instance_types:
        data = cache.get('%s:price:%s' % (cloud_provider.get_name(), instance_type))
        if data is None:
            logger.warning("No price data for %s?", instance_type)
            continue
        data = json.loads(data)
        for region in data:
            if region not in allowed_regions:
                continue
            for zone in data[region]:
                # look for blacklisted zone/type
                # zone+type is blacklisted because a previous spot request timed-out
                if cache.get("%s:blacklist:%s:%s" % (cloud_provider.get_name(), zone,
                                                     instance_type)) is not None:
                    logger.debug("%s/%s/%s is blacklisted", cloud_provider.get_name(), zone, instance_type)
                    continue

                # calculate price per core
                prices = [price / cores_per_instance[instance_type] for price in data[region][zone]]

                # Do not consider a zone/region combination that has a current
                # price higher than the maximum price we are willing to pay,
                # even if the median would end up being lower than our maximum.
                if prices[0] > cloud_provider.get_max_price(config):
                    rejected_prices[zone] = min(rejected_prices.get(zone, 9999), prices[0])
                    continue

                median = get_price_median(prices)
                if best_median is None or best_median > median:
                    best_median = median
                    best_zone = zone
                    best_region = region
                    best_type = instance_type
                    logger.debug("Best price median currently %r in %s/%s (%s)",
                                 best_median, best_region, best_zone, best_type)

    return (best_region, best_zone, best_type, rejected_prices)


def _start_pool_instances(pool, config, count=1):
    """ Start an instance with the given configuration """
    from .models import Instance, PoolStatusEntry, POOL_STATUS_ENTRY_TYPE

    cache = redis.StrictRedis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.REDIS_DB)

    try:
        # Figure out where to put our instances
        region, zone, instance_type, rejected_prices = _determine_best_location(config, count)

        priceLowEntries = PoolStatusEntry.objects.filter(pool=pool, type=POOL_STATUS_ENTRY_TYPE['price-too-low'])

        if not region:
            logger.warning("[Pool %d] No allowed region was cheap enough to spawn instances.", pool.id)

            if not priceLowEntries:
                entry = PoolStatusEntry()
                entry.pool = pool
                entry.type = POOL_STATUS_ENTRY_TYPE['price-too-low']
                entry.msg = "No allowed regions was cheap enough to spawn instances."
                for zone in rejected_prices:
                    entry.msg += "\n%s at %s" % (zone, rejected_prices[zone])
                entry.save()
            return

        elif priceLowEntries:
            priceLowEntries.delete()

        cloud_provider = CloudProvider.get_instance(PROVIDERS[0])  # TODO: support multiple providers
        image_name = cloud_provider.get_image_name(config)
        cores_per_instance = cloud_provider.get_cores_per_instance()

        # convert count from cores to instances
        #
        # if we have chosen the smallest possible instance that will put us over the requested core count,
        #   we will only be spawning 1 instance
        #
        # otherwise there may be a remainder if this is not an even division. let that be handled in the next tick
        #   so that the next smallest instance will be considered
        #
        # eg. need 12 cores, and allow instances sizes of 4 and 8 cores,
        #     8-core instance costs $0.24 ($0.03/core)
        #     4-core instance costs $0.16 ($0.04/core)
        #
        #     -> we will only request 1x 8-core instance this time around, leaving the required count at 4
        #     -> next time around, we will request 1x 4-core instance
        count = max(1, count // cores_per_instance[instance_type])

        userdata = _setup_userdata(config, pool)

        image_key = "%s:image:%s:%s" % (cloud_provider.get_name(), region, image_name)
        image = cache.get(image_key)

        if image is None:
            image = cloud_provider.get_image(region, config)
            cache.set(image_key, image, ex=24 * 3600)

        requested_instances = cloud_provider.start_instances(config, region, zone, userdata,
                                                             image, instance_type, count)

        for requested_instance in requested_instances:
            instance = Instance()
            instance.instance_id = requested_instance
            instance.region = region
            instance.zone = zone
            instance.status_code = INSTANCE_STATE["requested"]
            instance.pool = pool
            instance.size = cores_per_instance[instance_type]
            instance.save()

    except CloudProviderError as err:
        _update_pool_status(pool, err.TYPE, err.message)
    except Exception as msg:
        _update_pool_status(pool, 'unclassified', str(msg))


def _setup_userdata(config, pool):
    userdata = config.userdata.decode('utf-8')

    # Copy the userdata_macros and populate with internal variables
    userdata_macros = dict(config.userdata_macros)
    userdata_macros["EC2SPOTMANAGER_POOLID"] = str(pool.id)
    userdata_macros["EC2SPOTMANAGER_CYCLETIME"] = str(config.cycle_interval)

    userdata = UserData.handle_tags(userdata, userdata_macros)

    if not userdata:
        logger.error("[Pool %d] Failed to compile userdata.", pool.id)
        raise Exception("Configuration error: Failed to compile userdata")

    return userdata


def _terminate_pool_instances(running_instances, instance_pool):
    """ Terminate an instance with the given configuration """
    cloud_provider = CloudProvider.get_instance(PROVIDERS[0])  # TODO: support multiple providers
    instance_ids = _get_instance_ids_by_region(running_instances)
    try:
        cloud_provider.terminate_instances(instance_ids)
    except CloudProviderError as err:
        _update_pool_status(instance_pool, err.TYPE, err.message)
    except Exception as msg:
        _update_pool_status(instance_pool, 'unclassified', str(msg))


def _get_instance_ids_by_region(instances):
    instance_ids_by_region = {}

    for instance in instances:
        if instance.region not in instance_ids_by_region:
            instance_ids_by_region[instance.region] = []
        instance_ids_by_region[instance.region].append(instance.instance_id)

    return instance_ids_by_region


def _get_instances_by_ids(instances):
    instances_by_ids = {}
    for instance in instances:
        instances_by_ids[instance.instance_id] = instance
    return instances_by_ids


def _update_pool_status(pool, type_, message):
    from .models import PoolStatusEntry, POOL_STATUS_ENTRY_TYPE
    entry = PoolStatusEntry()
    entry.type = POOL_STATUS_ENTRY_TYPE[type_]
    entry.pool = pool
    entry.msg = message
    entry.isCritical = True
    entry.save()


def _update_pool_instances(pool, config):
    """Check the state of the instances in a pool and update it in the database"""
    from .models import Instance, PoolStatusEntry, POOL_STATUS_ENTRY_TYPE

    debug_cloud_instances_ids_seen = set()
    debug_not_updatable_continue = set()
    debug_not_in_region = {}

    cache = redis.StrictRedis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.REDIS_DB)
    cloud_provider = CloudProvider.get_instance(PROVIDERS[0])  # TODO: support multiple providers

    instances = Instance.objects.filter(pool=pool)
    instance_ids_by_region = _get_instance_ids_by_region(instances)
    instances_by_ids = _get_instances_by_ids(instances)
    instances_left = []
    instances_created = False

    debug_cloud_instance_ids_seen = set()
    debug_not_updatable_continue = set()
    debug_not_in_region = {}

    for instance in instances_by_ids.values():
        if instance.status_code != INSTANCE_STATE['requested']:
            instances_left.append(instance)

    # set config to this pool for now in case we set tags on fulfilled spot requests
    tags = cloud_provider.get_tags(config)
    tags[SPOTMGR_TAG + '-PoolId'] = str(pool.pk)

    for region in instance_ids_by_region:
        try:
            # first check status of pending spot requests
            requested = []
            for instance_id in instance_ids_by_region[region]:
                if instances_by_ids[instance_id].status_code == INSTANCE_STATE['requested']:
                    requested.append(instance_id)

            if requested:
                (successful_requests, failed_requests) = cloud_provider.check_instances_requests(
                    region, requested, cloud_provider.get_tags(config))

                for req_id in successful_requests:
                    instance = instances_by_ids[req_id]
                    instance.hostname = successful_requests[req_id]['hostname']
                    instance.instance_id = successful_requests[req_id]['instance_id']
                    instance.status_code = successful_requests[req_id]['status_code']
                    instance.save()

                    del instances_by_ids[req_id]
                    instances_by_ids[successful_requests[req_id]['instance_id']] = instance
                    instance_ids_by_region[region].append(successful_requests[req_id]['instance_id'])

                    instances_created = True

                for req_id in failed_requests:
                    instance = instances_by_ids[req_id]
                    if failed_requests[req_id]['action'] == 'blacklist':
                        # request was not fulfilled for some reason.. blacklist this type/zone for a while
                        inst = instances_by_ids[req_id]
                        key = "%s:blacklist:%s:%s" % (cloud_provider.get_name(), inst.zone,
                                                      failed_requests[req_id]['instance_type'])
                        cache.set(key, "", ex=12 * 3600)
                        logger.warning("Blacklisted %s for 12h", key)
                        inst.delete()
                    elif failed_requests[req_id]['action'] == 'disable_pool':
                        _update_pool_status(pool, 'unclassifed', 'request failed')

            cloud_instances = cloud_provider.check_instances_state(pool.pk, region)

            for cloud_instance in cloud_instances:
                debug_cloud_instances_ids_seen.add(cloud_instance)

                if (SPOTMGR_TAG + "-Updatable" not in cloud_instances[cloud_instance]['tags'] or
                        int(cloud_instances[cloud_instance]['tags'][SPOTMGR_TAG + "-Updatable"]) <= 0):
                    # The instance is not marked as updatable. We must not touch it because
                    # a spawning thread is still managing this instance. However, we must also
                    # remove this instance from the instances_left list if it's already in our
                    # database, because otherwise our code here would delete it from the database.
                    if cloud_instance in instance_ids_by_region[region]:
                        instances_left.remove(instances_by_ids[cloud_instance])
                    else:
                        debug_not_updatable_continue.add(cloud_instance)
                    continue

                instance = None

                # Whenever we see an instance that is not in our instance list for that region,
                # make sure it's a terminated instance because we should never have a running
                # instance that matches the search above but is not in our database.
                if cloud_instance not in instance_ids_by_region[region]:
                    if (cloud_instances[cloud_instance]['status']
                            not in [INSTANCE_STATE['shutting-down'], INSTANCE_STATE['terminated']]):

                        # As a last resort, try to find the instance in our database.
                        # If the instance was saved to our database between the entrance
                        # to this function and the search query sent to provider, then the instance
                        # will not be in our instances list but returned by provider. In this
                        # case, we try to load it directly from the database.
                        q = Instance.objects.filter(instance_id=cloud_instance)
                        if q:
                            instance = q[0]
                            logger.error("[Pool %d] Instance with ID %s was reloaded from database.",
                                         pool.id, cloud_instance)
                        else:
                            logger.error("[Pool %d] Instance with ID %s is not in database",
                                         pool.id, cloud_instance)

                            # Terminate at this point, we run in an inconsistent state
                            assert False
                    debug_not_in_region[cloud_instance] = cloud_instances[cloud_instance]['status']
                    continue

                instance = instances_by_ids[cloud_instance]
                if instance in instances_left:
                    instances_left.remove(instance)

                # Check the status code and update if necessary
                if instance.status_code != cloud_instances[cloud_instance]['status']:
                    instance.status_code = cloud_instances[cloud_instance]['status']
                    instance.save()

        except CloudProviderError as err:
            _update_pool_status(pool, err.TYPE, err.message)
            return
        except Exception as msg:
            _update_pool_status(pool, 'unclassified', str(msg))
            return

    for instance in instances_left:
        reasons = []

        if instance.instance_id not in debug_cloud_instance_ids_seen:
            reasons.append("no corresponding machine on cloud")

        if instance.instance_id in debug_not_updatable_continue:
            reasons.append("not updatable")

        if instance.instance_id in debug_not_in_region:
            reasons.append("has state code %s on cloud but not in our region"
                           % debug_not_in_region[instance.instance_id])

        if not reasons:
            reasons.append("?")

        logger.info("[Pool %d] Deleting instance with cloud instance ID %s from our database: %s",
                    pool.id, instance.instance_id, ", ".join(reasons))
        instance.delete()

    if instances_created:
        # Delete certain warnings we might have created earlier that no longer apply

        # If we ever exceeded the maximum spot instance count, we can clear
        # the warning now because we obviously succeeded in starting some instances.
        PoolStatusEntry.objects.filter(
            pool=pool, type=POOL_STATUS_ENTRY_TYPE['max-spot-instance-count-exceeded']).delete()

        # The same holds for temporary failures of any sort
        PoolStatusEntry.objects.filter(pool=pool, type=POOL_STATUS_ENTRY_TYPE['temporary-failure']).delete()

        # Do not delete unclassified errors here for now, so the user can see them.
