import json
import itertools
import logging
import sys
import celery
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
def _terminate_instance_ids(provider, region, instance_ids):
    cloud_provider = CloudProvider.get_instance(provider)
    try:
        cloud_provider.terminate_instances({region: instance_ids})
    except CloudProviderError as err:
        _update_provider_status(provider, err.TYPE, err.message)
    except Exception as msg:
        _update_provider_status(provider, 'unclassified', str(msg))


@app.task
def _terminate_instance_request_ids(provider, region, request_ids):
    cloud_provider = CloudProvider.get_instance(provider)
    try:
        cloud_provider.cancel_requests({region: request_ids})
    except CloudProviderError as err:
        _update_provider_status(provider, err.TYPE, err.message)
    except Exception as msg:
        _update_provider_status(provider, 'unclassified', str(msg))


def _determine_best_location(config, count, cache=None):
    from .models import Instance, ProviderStatusEntry

    if cache is None:
        cache = redis.StrictRedis.from_url(settings.REDIS_URL)

    best_provider = None
    best_zone = None
    best_region = None
    best_type = None
    best_median = None
    best_instances = None
    rejected_prices = {}

    for provider in PROVIDERS:
        cloud_provider = CloudProvider.get_instance(provider)

        if not cloud_provider.config_supported(config):
            continue

        if ProviderStatusEntry.objects.filter(provider=provider, isCritical=True).exists():
            continue

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
                    if cache.get("%s:blacklist:%s:%s:%s" % (cloud_provider.get_name(), region, zone,
                                                            instance_type)) is not None:
                        logger.debug("%s/%s/%s/%s is blacklisted", cloud_provider.get_name(), region, zone,
                                     instance_type)
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
                    if best_median is None or median <= best_median:
                        # don't care about excluding stopped/stopping, as we just want to know how "busy" the zone is
                        instances = int(Instance.objects.filter(provider=provider, region=region, zone=zone).count())
                        if median == best_median and instances >= best_instances:
                            continue
                        best_provider = provider
                        best_median = median
                        best_zone = zone
                        best_region = region
                        best_type = instance_type
                        best_instances = instances
                        logger.debug("Best price median currently %r in %s/%s (%s, %d instances)",
                                     best_median, best_region, best_zone, best_type, best_instances)

    return (best_provider, best_region, best_zone, best_type, rejected_prices)


def _start_pool_instances(pool, config, count=1):
    """ Start an instance with the given configuration """
    from .models import Instance, PoolStatusEntry, POOL_STATUS_ENTRY_TYPE

    cache = redis.StrictRedis.from_url(settings.REDIS_URL)

    try:
        # Figure out where to put our instances
        provider, region, zone, instance_type, rejected_prices = _determine_best_location(config, count, cache=cache)

        priceLowEntries = PoolStatusEntry.objects.filter(pool=pool, type=POOL_STATUS_ENTRY_TYPE['price-too-low'])

        if not region:
            logger.warning("[Pool %d] No allowed region was cheap enough to spawn instances.", pool.id)

            if not priceLowEntries:
                msg = "No allowed region was cheap enough to spawn instances."
                for zone in rejected_prices:
                    msg += "\n%s at %s" % (zone, rejected_prices[zone])
                _update_pool_status(pool, 'price-too-low', msg)
            return

        elif priceLowEntries:
            priceLowEntries.delete()

        cloud_provider = CloudProvider.get_instance(provider)
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

        userdata = None
        if provider == 'EC2Spot':
            # setup userdata
            userdata = config.ec2_userdata.decode('utf-8')

            # Copy the userdata_macros and populate with internal variables
            userdata_macros = dict(config.ec2_userdata_macros)
            userdata_macros["EC2SPOTMANAGER_POOLID"] = str(pool.id)
            userdata_macros["EC2SPOTMANAGER_PROVIDER"] = provider
            userdata_macros["EC2SPOTMANAGER_CYCLETIME"] = str(config.cycle_interval)

            userdata = UserData.handle_tags(userdata, userdata_macros)

            if not userdata:
                logger.error("[Pool %d] Failed to compile userdata.", pool.id)
                _update_pool_status(pool, "config-error", "Configuration error: Failed to compile userdata")
                return

        elif provider == 'GCE':
            config.gce_env["EC2SPOTMANAGER_POOLID"] = str(pool.id)
            config.gce_env["EC2SPOTMANAGER_PROVIDER"] = provider
            config.gce_env["EC2SPOTMANAGER_CYCLETIME"] = str(config.cycle_interval)

        image_key = "%s:image:%s:%s" % (cloud_provider.get_name(), region, image_name)
        image = cache.get(image_key)

        if image is None:
            image = cloud_provider.get_image(region, config)
            cache.set(image_key, image, ex=24 * 3600)

        tags = cloud_provider.get_tags(pool.config.flatten())
        tags[SPOTMGR_TAG + '-PoolId'] = str(pool.pk)

        requested_instances = cloud_provider.start_instances(config, region, zone, userdata,
                                                             image, instance_type, count, tags)

        for instance_name, requested_instance in requested_instances.items():
            instance = Instance()
            instance.instance_id = instance_name
            instance.hostname = requested_instance['hostname']
            instance.region = region
            instance.zone = zone
            instance.status_code = requested_instance['status_code']
            instance.pool = pool
            instance.size = cores_per_instance[instance_type]
            instance.provider = provider
            instance.save()

    except CloudProviderError as err:
        _update_pool_status(pool, err.TYPE, err.message)
    except Exception as msg:
        _update_pool_status(pool, 'unclassified', str(msg))


def _update_provider_status(provider, type_, message):
    from .models import ProviderStatusEntry, POOL_STATUS_ENTRY_TYPE

    is_critical = type_ not in {'max-spot-instance-count-exceeded', 'price-too-low', 'temporary-failure'}

    if not ProviderStatusEntry.objects.filter(type=POOL_STATUS_ENTRY_TYPE[type_],
                                              provider=provider,
                                              msg=message,
                                              isCritical=is_critical).exists():
        entry = ProviderStatusEntry()
        entry.type = POOL_STATUS_ENTRY_TYPE[type_]
        entry.provider = provider
        entry.msg = message
        entry.isCritical = is_critical
        entry.save()
        logger.error('Logging ProviderStatusEntry(%s): %s (critical=%r)', provider, message, is_critical)
        if sys.exc_info()[0] is not None:
            logger.exception("ProviderStatusEntry backtrace:")
    else:
        logger.warning('Ignoring provider error: already exists.')


def _update_pool_status(pool, type_, message):
    from .models import PoolStatusEntry, POOL_STATUS_ENTRY_TYPE

    is_critical = type_ not in {'max-spot-instance-count-exceeded', 'price-too-low', 'temporary-failure'}

    if not PoolStatusEntry.objects.filter(type=POOL_STATUS_ENTRY_TYPE[type_],
                                          pool=pool,
                                          msg=message,
                                          isCritical=is_critical).exists():
        entry = PoolStatusEntry()
        entry.type = POOL_STATUS_ENTRY_TYPE[type_]
        entry.pool = pool
        entry.msg = message
        entry.isCritical = is_critical
        entry.save()
        logger.error('Logging PoolStatusEntry(%d): %s (critical=%r)', pool.pk, message, is_critical)
        if sys.exc_info()[0] is not None:
            logger.exception("PoolStatusEntry backtrace:")
    else:
        logger.warning('Ignoring pool error: already exists.')


@app.task
def update_requests(provider, region, pool_id):
    """Update all requests in a given provider/region/pool.

    @ptype provider: str
    @param provider: CloudProvider name

    @ptype region: str
    @param region: Region name within the given provider

    @ptype pool_id: int
    @param pool_id: InstancePool pk
    """
    from .models import Instance, InstancePool, PoolStatusEntry, ProviderStatusEntry, POOL_STATUS_ENTRY_TYPE

    logger.debug("-> update_requests(%r, %r, %r)", provider, region, pool_id)

    try:
        cache = redis.StrictRedis.from_url(settings.REDIS_URL)
        cloud_provider = CloudProvider.get_instance(provider)

        requested = {}  # provider_request_id -> Instance
        instances_created = False
        for instance in Instance.objects.filter(provider=provider, region=region, pool_id=pool_id,
                                                status_code=INSTANCE_STATE['requested']):
            requested[instance.instance_id] = instance

        # check status of requested instances
        if requested:
            pool = InstancePool.objects.get(pk=pool_id)

            tags = cloud_provider.get_tags(pool.config.flatten())
            tags[SPOTMGR_TAG + '-PoolId'] = str(pool.pk)

            (successful_requests, failed_requests) = cloud_provider.check_instances_requests(
                region, list(requested), tags)

            for req_id in successful_requests:
                instance = requested[req_id]
                instance.created = timezone.now()  # reset creation time now that the instance really exists
                instance.hostname = successful_requests[req_id]['hostname']
                instance.instance_id = successful_requests[req_id]['instance_id']
                instance.status_code = successful_requests[req_id]['status_code']
                instance.save()

                instances_created = True

            for req_id in failed_requests:
                instance = requested[req_id]
                if failed_requests[req_id]['action'] == 'blacklist':
                    # request was not fulfilled for some reason.. blacklist this type/region/zone for a while
                    key = "%s:blacklist:%s:%s:%s" % (provider, instance.region, instance.zone,
                                                     failed_requests[req_id]['instance_type'])
                    cache.set(key, "", ex=12 * 3600)
                    logger.warning("Blacklisted %s for 12h", key)
                    instance.delete()
                    _update_pool_status(pool, 'temporary-failure', failed_requests[req_id]['reason'])
                elif failed_requests[req_id]['action'] == 'disable_pool':
                    _update_pool_status(pool, 'unclassified', 'request failed')

        if instances_created:
            # Delete certain warnings we might have created earlier that no longer apply

            # If we ever exceeded the maximum spot instance count, we can clear
            # the warning now because we obviously succeeded in starting some instances.
            # The same holds for temporary failures of any sort
            PoolStatusEntry.objects.filter(
                pool=pool, type__in=(POOL_STATUS_ENTRY_TYPE['max-spot-instance-count-exceeded'],
                                     POOL_STATUS_ENTRY_TYPE['temporary-failure'])).delete()

            ProviderStatusEntry.objects.filter(
                provider=provider, type__in=(POOL_STATUS_ENTRY_TYPE['max-spot-instance-count-exceeded'],
                                             POOL_STATUS_ENTRY_TYPE['temporary-failure'])).delete()

            # Do not delete unclassified errors here for now, so the user can see them.

    except CloudProviderError as err:
        logger.exception("[Pool %d] cloud provider raised", pool.id)
        _update_pool_status(pool, err.TYPE, err.message)
    except Exception as msg:
        logger.exception("[Pool %d] update_requests raised", pool.id)
        _update_pool_status(pool, 'unclassified', str(msg))


@app.task
def update_instances(provider, region):
    """Reconcile database instances with cloud provider for a given provider/region.

    @ptype provider: str
    @param provider: CloudProvider name

    @ptype region: str
    @param region: Region name within the given provider
    """
    from .models import Instance

    logger.debug("-> update_instances(%r, %r)", provider, region)

    try:
        cloud_provider = CloudProvider.get_instance(provider)

        debug_cloud_instance_ids_seen = set()
        debug_not_updatable_continue = set()
        debug_not_in_region = {}

        instances = {}  # provider_id -> Instance
        instances_left = set()  # Instance
        for instance in Instance.objects.filter(provider=provider, region=region) \
                .exclude(status_code=INSTANCE_STATE['requested']):
            instances[instance.instance_id] = instance
            instances_left.add(instance)

        # reconcile instance state from provider with DB
        cloud_instances = cloud_provider.check_instances_state(None, region)
        for cloud_id, cloud_data in cloud_instances.items():
            debug_cloud_instance_ids_seen.add(cloud_id)

            if (SPOTMGR_TAG + "-Updatable" not in cloud_data['tags'] or
                    int(cloud_data['tags'][SPOTMGR_TAG + "-Updatable"]) <= 0):

                logger.warning("*************** INSTANCE %s in %s/%s NOT UPDATABLE ***************",
                               cloud_id, provider, region)
                logger.warning("see: https://github.com/MozillaSecurity/FuzzManager/pull/550#discussion_r284260225")

                # The instance is not marked as updatable. We must not touch it because
                # a spawning thread is still managing this instance. However, we must also
                # remove this instance from the instances_left list if it's already in our
                # database, because otherwise our code here would delete it from the database.
                if cloud_id in instances:
                    if instances[cloud_id] in instances_left:
                        instances_left.remove(instances[cloud_id])
                else:
                    debug_not_updatable_continue.add(cloud_id)
                continue

            instance = None

            # Whenever we see an instance that is not in our instance list for that region,
            # make sure it's a terminated instance because we should never have a running
            # instance that matches the search above but is not in our database.
            if cloud_id not in instances:
                if cloud_data['status'] not in {INSTANCE_STATE['shutting-down'], INSTANCE_STATE['terminated']}:

                    # As a last resort, try to find the instance in our database.
                    # If the instance was saved to our database between the entrance
                    # to this function and the search query sent to provider, then the instance
                    # will not be in our instances list but returned by provider. In this
                    # case, we try to load it directly from the database.
                    q = Instance.objects.filter(instance_id=cloud_id)
                    if q:
                        instance = q[0]
                        logger.error("[Pool %d] Instance with ID %s was reloaded from database.", q.pool_id, cloud_id)
                    else:
                        logger.error("[Pool ?] Instance with ID %s is not in database", cloud_id)

                        # Terminate at this point, we run in an inconsistent state
                        raise RuntimeError("Database and cloud provider are inconsistent")

                debug_not_in_region[cloud_id] = cloud_data['status']
                continue

            instance = instances[cloud_id]
            if instance in instances_left:
                instances_left.remove(instance)

            # Check the status code and update if necessary
            if instance.status_code != cloud_data['status']:
                instance.status_code = cloud_data['status']
                instance.save()

        for instance in instances_left:
            reasons = []

            if instance.instance_id not in debug_cloud_instance_ids_seen:
                if timezone.now() - instance.created < timezone.timedelta(minutes=5):
                    logger.warning("[Pool %d] Machine %s has no corresponding machine in %s/%s, "
                                   "not deleting until it is at least 5 minutes old.",
                                   instance.pool_id, instance.instance_id, instance.provider, instance.region)
                    continue
                reasons.append("no corresponding machine on cloud")

            if instance.instance_id in debug_not_updatable_continue:
                reasons.append("not updatable")

            if instance.instance_id in debug_not_in_region:
                reasons.append("has state code %s on cloud but not in our region"
                               % debug_not_in_region[instance.instance_id])

            if not reasons:
                reasons.append("?")

            logger.info("[Pool %d] Deleting instance with cloud instance ID %s from our database: %s",
                        instance.pool_id, instance.instance_id, ", ".join(reasons))
            instance.delete()

    except CloudProviderError as err:
        logger.exception("[Provider %s] cloud provider raised", provider)
        _update_provider_status(provider, err.TYPE, err.message)
    except Exception as msg:
        logger.exception("[Provider %s] update_instances raised", provider)
        _update_provider_status(provider, 'unclassified', str(msg))


@app.task
def cycle_and_terminate_disabled(provider, region):
    """Kill off instances if pools need to be cycled or disabled.

    @ptype provider: str
    @param provider: CloudProvider name

    @ptype region: str
    @param region: Region name within the given provider
    """
    from .models import Instance, PoolStatusEntry, ProviderStatusEntry

    logger.debug("-> cycle_and_terminate_disabled(%r, %r)", provider, region)

    provider_has_critical_error = ProviderStatusEntry.objects.filter(provider=provider, isCritical=True).exists()

    try:
        # check if the pool has any instances to be terminated
        requests_to_terminate = []
        instances_to_terminate = []
        instances_by_pool = {}
        pool_disable = {}  # pool_id -> reason (or blank for enabled)
        for instance in Instance.objects.filter(provider=provider, region=region):
            if instance.pool_id not in pool_disable:
                pool = instance.pool
                if provider_has_critical_error:
                    pool_disable[instance.pool_id] = "Provider error"
                elif PoolStatusEntry.objects.filter(pool=pool, isCritical=True).exists():
                    pool_disable[instance.pool_id] = "Pool error"
                elif not pool.isEnabled:
                    pool_disable[instance.pool_id] = "Disabled"
                elif pool.last_cycled is None or \
                        pool.last_cycled + timezone.timedelta(seconds=pool.config.flatten().cycle_interval) \
                        < timezone.now():
                    pool_disable[instance.pool_id] = "Needs to be cycled"
                else:
                    pool_disable[instance.pool_id] = ""

            if pool_disable[instance.pool_id]:
                if instance.status_code not in {INSTANCE_STATE['shutting-down'], INSTANCE_STATE['terminated']}:
                    instances_by_pool.setdefault(instance.pool_id, 0)
                    instances_by_pool[instance.pool_id] += 1
                if instance.status_code == INSTANCE_STATE['requested']:
                    requests_to_terminate.append(instance.instance_id)
                elif instance.status_code not in {INSTANCE_STATE['shutting-down'], INSTANCE_STATE['terminated']}:
                    instances_to_terminate.append(instance.instance_id)

        for pool_id, count in instances_by_pool.items():
            logger.info("[Pool %d] %s, terminating %d instances in %s/%s...", pool_id, pool_disable[pool_id], count,
                        provider, region)
        if requests_to_terminate:
            _terminate_instance_request_ids.delay(provider, region, requests_to_terminate)
        if instances_to_terminate:
            _terminate_instance_ids.delay(provider, region, instances_to_terminate)

    except CloudProviderError as err:
        logger.exception("[Provider %s] cloud provider raised", provider)
        _update_provider_status(provider, err.TYPE, err.message)
    except Exception as msg:
        logger.exception("[Provider %s] cycle_and_terminate_disabled raised", provider)
        _update_provider_status(provider, 'unclassified', str(msg))


@app.task
def check_and_resize_pool(pool_id):
    """Check pool size and either request more instances from cheapest provider/region,
    or terminate unneeded instances.

    @ptype pool_id: int
    @param pool_id: InstancePool pk
    """
    from .models import Instance, InstancePool, PoolStatusEntry

    logger.debug("-> check_and_resize_pool(%r)", pool_id)

    if PoolStatusEntry.objects.filter(pool_id=pool_id, isCritical=True).exists():
        return []

    try:
        pool = InstancePool.objects.get(pk=pool_id)

        # check config
        if pool.config.isCyclic():
            _update_pool_status(pool, "config-error", "Configuration error (cyclic).")
            return []

        missing = pool.config.getMissingParameters()
        if missing:
            _update_pool_status(pool, "config-error", "Configuration error (missing: %r)." % (missing,))
            return []

        config = pool.config.flatten()

        # if any pools need cycling, that will be complete now, so update the time
        if pool.last_cycled is None or \
                pool.last_cycled + timezone.timedelta(seconds=config.cycle_interval) < timezone.now():
            logger.info("[Pool %d] All instances cycled.", pool_id)
            pool.last_cycled = timezone.now()
            pool.save()

        instance_cores_missing = config.size
        running_instances = []

        instances = Instance.objects.filter(pool=pool)

        for instance in instances:
            if instance.status_code in [INSTANCE_STATE['running'], INSTANCE_STATE['pending'],
                                        INSTANCE_STATE['requested']]:
                instance_cores_missing -= instance.size
                running_instances.append(instance)
            elif instance.status_code in [INSTANCE_STATE['shutting-down'], INSTANCE_STATE['terminated']]:
                # The instance is no longer running, delete it from our database
                logger.info("[Pool %d] Deleting terminated instance with ID %s from our database.",
                            pool_id, instance.instance_id)
                instance.delete()
            else:
                instance_cores_missing -= instance.size
                running_instances.append(instance)

        # Continue working with the instances we have running
        instances = running_instances

        if instance_cores_missing > 0:
            logger.info("[Pool %d] Needs %s more instance cores, starting...",
                        pool_id, instance_cores_missing)
            _start_pool_instances(pool, config, count=instance_cores_missing)

        elif instance_cores_missing < 0:
            # Select the oldest instances we have running and terminate
            # them so we meet the size limitation again.
            instances = []
            for instance in Instance.objects.filter(pool=pool).order_by('created'):
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
                logger.info("[Pool %d] Has %d instance cores over limit in %d instances, queuing for termination...",
                            pool_id, instance_cores_missing, len(instances))
                return [instance.id for instance in instances]
        else:
            logger.debug("[Pool %d] Size is ok.", pool_id)

    except CloudProviderError as err:
        _update_pool_status(pool, err.TYPE, err.message)
    except Exception as msg:
        _update_pool_status(pool, 'unclassified', str(msg))

    return []


@app.task
def terminate_instances(pool_instances):
    """Terminate a given list of instances.

    @ptype pool_instances: list of lists of instance ids
    @param pool_instances: Takes the results from multiple calls to check_and_resize_pool(), and aggregates the results
                           into one call to terminate instances/requests per provider/region.
    """
    from .models import Instance

    logger.debug("-> terminate_instances(%r)", pool_instances)

    instances_by_provider_region = {}
    for instance in Instance.objects.filter(pk__in=itertools.chain.from_iterable(pool_instances)):
        requested, running = instances_by_provider_region.setdefault((instance.provider, instance.region), ([], []))
        if instance.status_code == INSTANCE_STATE['requested']:
            requested.append(instance.instance_id)
        else:
            running.append(instance.instance_id)

    provider_parallel = []
    for (provider, region), (requested, running) in instances_by_provider_region.items():
        if requested:
            provider_parallel.append(_terminate_instance_request_ids.si(provider, region, requested))
        if running:
            provider_parallel.append(_terminate_instance_ids.si(provider, region, running))
    celery.group(provider_parallel).delay()
