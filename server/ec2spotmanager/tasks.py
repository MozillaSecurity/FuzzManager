import logging
import socket
import ssl
import traceback
import boto.ec2
import boto.exception
import fasteners
from django.utils import timezone
from laniakea.core.manager import Laniakea
from laniakea import LaniakeaCommandLine
from celeryconf import app
from . import cron  # noqa ensure cron tasks get registered
from .common.prices import get_spot_prices, get_price_median


logger = logging.getLogger("ec2spotmanager")


SPOTMGR_TAG = "SpotManager"


@app.task
def check_instance_pool(pool_id):
    from .models import Instance, InstancePool, INSTANCE_STATE, PoolStatusEntry, POOL_STATUS_ENTRY_TYPE

    lock = fasteners.InterProcessLock('/tmp/ec2spotmanager.pool%d.lck' % pool_id)

    if not lock.acquire(blocking=False):
        logger.warning('[Pool %d] Another check still in progress, exiting.', pool_id)
        return

    try:

        instance_pool = InstancePool.objects.get(pk=pool_id)

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

        instances_missing = config.size
        running_instances = []

        _update_pool_instances(instance_pool, config)

        instances = Instance.objects.filter(pool=instance_pool)

        for instance in instances:
            instance_status_code_fixed = False
            if instance.status_code >= 256:
                logger.warning("[Pool %d] Instance with EC2 ID %s has weird state code %d, attempting to fix...",
                               instance_pool.id, instance.ec2_instance_id, instance.status_code)
                instance.status_code -= 256
                instance_status_code_fixed = True

            if instance.status_code in [INSTANCE_STATE['running'], INSTANCE_STATE['pending'],
                                        INSTANCE_STATE['requested']]:
                instances_missing -= 1
                running_instances.append(instance)
            elif instance.status_code in [INSTANCE_STATE['shutting-down'], INSTANCE_STATE['terminated']]:
                # The instance is no longer running, delete it from our database
                logger.info("[Pool %d] Deleting terminated instance with EC2 ID %s from our database.",
                            instance_pool.id, instance.ec2_instance_id)
                instance.delete()
            else:
                if instance_status_code_fixed:
                    # Restore original status code for error reporting
                    instance.status_code += 256

                logger.error("[Pool %d] Instance with EC2 ID %s has unexpected state code %d",
                             instance_pool.id, instance.ec2_instance_id, instance.status_code)
                # In some cases, EC2 sends undocumented status codes and we don't know why
                # For now, reset the status code to 0, consider the instance still present
                # and hope that with the next update iteration, the problem will be gone.
                instance.status_code = 0
                instance.save()
                instances_missing -= 1
                running_instances.append(instance)

        # Continue working with the instances we have running
        instances = running_instances

        if not instance_pool.isEnabled:
            if running_instances:
                _terminate_pool_instances(instance_pool, running_instances, config, terminateByPool=True)

            return

        if ((not instance_pool.last_cycled) or
                instance_pool.last_cycled < timezone.now() - timezone.timedelta(seconds=config.cycle_interval)):
            logger.info("[Pool %d] Needs to be cycled, terminating all instances...", instance_pool.id)
            instance_pool.last_cycled = timezone.now()
            _terminate_pool_instances(instance_pool, instances, config, terminateByPool=True)
            instance_pool.save()

            logger.info("[Pool %d] Termination complete.", instance_pool.id)

        if instances_missing > 0:
            logger.info("[Pool %d] Needs %s more instances, starting...",
                        instance_pool.id, instances_missing)
            _start_pool_instances(instance_pool, config, count=instances_missing)
        elif instances_missing < 0:
            # Select the oldest instances we have running and terminate
            # them so we meet the size limitation again.
            logger.info("[Pool %d] Has %s instances over limit, terminating...",
                        instance_pool.id, -instances_missing)
            instances = Instance.objects.filter(pool=instance_pool).order_by('created')[:-instances_missing]
            _terminate_pool_instances(instance_pool, instances, config)
        else:
            logger.debug("[Pool %d] Size is ok.", instance_pool.id)

    finally:
        lock.release()


def _get_best_region_zone(config):
    prices = {instance_type: get_spot_prices(config.ec2_allowed_regions,
                                             config.aws_access_key_id,
                                             config.aws_secret_access_key,
                                             instance_type)
              for instance_type in config.ec2_instance_types}

    # Calculate median values for all availability zones and best zone/price
    best_zone = None
    best_region = None
    best_type = None
    best_median = None
    rejected_prices = {}
    for instance_type in prices:
        for region in prices[instance_type]:
            for zone in prices[instance_type][region]:
                # Do not consider a zone/region combination that has a current
                # price higher than the maximum price we are willing to pay,
                # even if the median would end up being lower than our maximum.
                if prices[instance_type][region][zone][0] > config.ec2_max_price:
                    rejected_prices[zone] = min(rejected_prices.get(zone, 9999),
                                                prices[instance_type][region][zone][0])
                    continue

                median = get_price_median(prices[instance_type][region][zone])
                if best_median is None or best_median > median:
                    best_median = median
                    best_zone = zone
                    best_region = region
                    best_type = instance_type
                    logger.debug("Best price median currently %r in %s/%s (%s)",
                                 median, best_region, best_zone, best_type)

    return (best_region, best_zone, best_type, rejected_prices)


def _create_laniakea_images(config):
    images = {"default": {}}

    # These are the configuration keys we want to put into the target configuration
    # without further preprocessing, except for the adjustment of the key name itself.
    keys = [
        'ec2_key_name',
        'ec2_image_name',
        'ec2_security_groups',
    ]

    for key in keys:
        lkey = key.replace("ec2_", "", 1)
        images["default"][lkey] = config[key]

    if config.ec2_raw_config:
        images["default"].update(config.ec2_raw_config)

    return images


def _start_pool_instances(pool, config, count=1):
    """ Start an instance with the given configuration """
    from .models import Instance, INSTANCE_STATE, PoolStatusEntry, POOL_STATUS_ENTRY_TYPE
    images = _create_laniakea_images(config)

    # Figure out where to put our instances
    try:
        (region, zone, instance_type, rejected) = _get_best_region_zone(config)
    except (boto.exception.EC2ResponseError, boto.exception.BotoServerError, ssl.SSLError, socket.error):
        # In case of temporary failures here, we will retry again in the next cycle
        logger.warning("[Pool %d] Failed to acquire spot instance prices: %s.", pool.id, traceback.format_exc())
        return
    except RuntimeError:
        logger.error("[Pool %d] Failed to compile userdata.", pool.id)
        entry = PoolStatusEntry()
        entry.type = POOL_STATUS_ENTRY_TYPE['config-error']
        entry.pool = pool
        entry.isCritical = True
        entry.msg = "Configuration error: %s" % traceback.format_exc()
        entry.save()
        return

    priceLowEntries = PoolStatusEntry.objects.filter(pool=pool, type=POOL_STATUS_ENTRY_TYPE['price-too-low'])

    if not region:
        logger.warning("[Pool %d] No allowed region was cheap enough to spawn instances.", pool.id)

        if not priceLowEntries:
            entry = PoolStatusEntry()
            entry.pool = pool
            entry.type = POOL_STATUS_ENTRY_TYPE['price-too-low']
            entry.msg = "No allowed region was cheap enough to spawn instances."
            for zone in rejected:
                entry.msg += "\n%s at %s" % (zone, rejected[zone])
            entry.save()
        return
    else:
        if priceLowEntries:
            priceLowEntries.delete()

    logger.debug("[Pool %d] Using instance type %s in region %s with availability zone %s.",
                 pool.id, instance_type, region, zone)

    try:
        userdata = LaniakeaCommandLine.handle_import_tags(config.ec2_userdata.decode('utf-8'))

        # Copy the userdata_macros and populate with internal variables
        ec2_userdata_macros = dict(config.ec2_userdata_macros)
        ec2_userdata_macros["EC2SPOTMANAGER_POOLID"] = str(pool.id)

        userdata = LaniakeaCommandLine.handle_tags(userdata, ec2_userdata_macros)
        if not userdata:
            logger.error("[Pool %d] Failed to compile userdata.", pool.id)

            entry = PoolStatusEntry()
            entry.type = POOL_STATUS_ENTRY_TYPE['config-error']
            entry.pool = pool
            entry.isCritical = True
            entry.msg = "Configuration error: Failed to compile userdata"
            entry.save()

            raise RuntimeError("start_pool_instances: Failed to compile userdata")

        images["default"]['user_data'] = userdata.encode("utf-8")
        images["default"]['placement'] = zone
        images["default"]['count'] = count
        images["default"]['instance_type'] = instance_type

        cluster = Laniakea(images)
        try:
            cluster.connect(region=region, aws_access_key_id=config.aws_access_key_id,
                            aws_secret_access_key=config.aws_secret_access_key)
        except ssl.SSLError as msg:
            logger.warning("[Pool %d] start_pool_instances: Temporary failure in region %s: %s",
                           pool.id, region, msg)
            entry = PoolStatusEntry()
            entry.pool = pool
            entry.type = POOL_STATUS_ENTRY_TYPE['temporary-failure']
            entry.msg = "Temporary failure occurred: %s" % msg
            entry.save()

            return

        except Exception as msg:
            logger.exception("[Pool %d] start_pool_instances: laniakea failure: %s", pool.id, msg)

            # Log this error to the pool status messages
            entry = PoolStatusEntry()
            entry.type = POOL_STATUS_ENTRY_TYPE['unclassified']
            entry.pool = pool
            entry.msg = str(msg)
            entry.isCritical = True
            entry.save()

            return

        try:
            logger.info("[Pool %d] Creating %d instances...", pool.id, count)
            for ec2_request in cluster.create_spot_requests(config.ec2_max_price,
                                                            delete_on_termination=True,
                                                            timeout=10 * 60):
                instance = Instance()
                instance.ec2_instance_id = ec2_request
                instance.ec2_region = region
                instance.ec2_zone = zone
                instance.status_code = INSTANCE_STATE["requested"]
                instance.pool = pool
                instance.save()

        except (boto.exception.EC2ResponseError, boto.exception.BotoServerError, ssl.SSLError, socket.error) as msg:
            if "MaxSpotInstanceCountExceeded" in str(msg):
                logger.warning("[Pool %d] start_pool_instances: Maximum instance count exceeded for region %s",
                               pool.id, region)
                if not PoolStatusEntry.objects.filter(
                        pool=pool, type=POOL_STATUS_ENTRY_TYPE['max-spot-instance-count-exceeded']):
                    entry = PoolStatusEntry()
                    entry.pool = pool
                    entry.type = POOL_STATUS_ENTRY_TYPE['max-spot-instance-count-exceeded']
                    entry.msg = "Auto-selected region exceeded its maximum spot instance count."
                    entry.save()
            elif "Service Unavailable" in str(msg):
                logger.warning("[Pool %d] start_pool_instances: Temporary failure in region %s: %s",
                               pool.id, region, msg)
                entry = PoolStatusEntry()
                entry.pool = pool
                entry.type = POOL_STATUS_ENTRY_TYPE['temporary-failure']
                entry.msg = "Temporary failure occurred: %s" % msg
                entry.save()
            else:
                logger.exception("[Pool %d] start_pool_instances: boto failure: %s", pool.id, msg)
                entry = PoolStatusEntry()
                entry.type = POOL_STATUS_ENTRY_TYPE['unclassified']
                entry.pool = pool
                entry.isCritical = True
                entry.msg = "Unclassified error occurred: %s" % msg
                entry.save()

    except Exception as msg:
        logger.exception("[Pool %d] start_pool_instances: unhandled failure: %s", pool.id, msg)
        raise


def _terminate_pool_instances(pool, instances, config, terminateByPool=False):
    """ Terminate an instance with the given configuration """
    from .models import INSTANCE_STATE, PoolStatusEntry, POOL_STATUS_ENTRY_TYPE
    instance_ids_by_region = _get_instance_ids_by_region(instances)

    for region in instance_ids_by_region:
        cluster = Laniakea(None)
        try:
            cluster.connect(region=region, aws_access_key_id=config.aws_access_key_id,
                            aws_secret_access_key=config.aws_secret_access_key)
        except Exception as msg:
            # Log this error to the pool status messages
            entry = PoolStatusEntry()
            entry.type = POOL_STATUS_ENTRY_TYPE['unclassified']
            entry.pool = pool
            entry.msg = str(msg)
            entry.isCritical = True
            entry.save()

            logger.exception("[Pool %d] terminate_pool_instances: laniakea failure: %s", pool.id, msg)
            return None

        try:
            if terminateByPool:
                boto_instances = cluster.find(filters={"tag:" + SPOTMGR_TAG + "-PoolId": str(pool.pk)})

                # Data consistency checks
                for boto_instance in boto_instances:
                    # state_code is a 16-bit value where the high byte is
                    # an opaque internal value and should be ignored.
                    state_code = boto_instance.state_code & 255
                    if not ((boto_instance.id in instance_ids_by_region[region]) or
                            (state_code == INSTANCE_STATE['shutting-down'] or
                             state_code == INSTANCE_STATE['terminated'])):
                        logger.error("[Pool %d] Instance with EC2 ID %s (status %d) "
                                     "is not in region list for region %s",
                                     pool.id, boto_instance.id, state_code, region)

                cluster.terminate(boto_instances)
            else:
                logger.info("[Pool %d] Terminating %s instances in region %s",
                            pool.id, len(instance_ids_by_region[region]), region)
                cluster.terminate(cluster.find(instance_ids=instance_ids_by_region[region]))
        except (boto.exception.EC2ResponseError, boto.exception.BotoServerError, ssl.SSLError, socket.error) as msg:
            logger.exception("[Pool %d] terminate_pool_instances: boto failure: %s", pool.id, msg)
            return 1


def _get_instance_ids_by_region(instances):
    instance_ids_by_region = {}

    for instance in instances:
        if instance.ec2_region not in instance_ids_by_region:
            instance_ids_by_region[instance.ec2_region] = []
        instance_ids_by_region[instance.ec2_region].append(instance.ec2_instance_id)

    return instance_ids_by_region


def _get_instances_by_ids(instances):
    instances_by_ids = {}
    for instance in instances:
        instances_by_ids[instance.ec2_instance_id] = instance
    return instances_by_ids


def _update_pool_instances(pool, config):
    """Check the state of the instances in a pool and update it in the database"""
    from .models import Instance, INSTANCE_STATE, PoolStatusEntry, POOL_STATUS_ENTRY_TYPE
    instances = Instance.objects.filter(pool=pool)
    instance_ids_by_region = _get_instance_ids_by_region(instances)
    instances_by_ids = _get_instances_by_ids(instances)
    instances_left = []
    instances_created = False

    debug_boto_instance_ids_seen = set()
    debug_not_updatable_continue = set()
    debug_not_in_region = {}

    for instance in instances_by_ids.values():
        if instance.status_code != INSTANCE_STATE['requested']:
            instances_left.append(instance)

    # set config to this pool for now in case we set tags on fulfilled spot requests
    config.ec2_tags[SPOTMGR_TAG + '-PoolId'] = str(pool.pk)

    for region in instance_ids_by_region:
        cluster = Laniakea(None)
        try:
            cluster.connect(region=region, aws_access_key_id=config.aws_access_key_id,
                            aws_secret_access_key=config.aws_secret_access_key)
        except Exception as msg:
            # Log this error to the pool status messages
            entry = PoolStatusEntry()
            entry.type = POOL_STATUS_ENTRY_TYPE['unclassified']
            entry.pool = pool
            entry.msg = str(msg)
            entry.isCritical = True
            entry.save()

            logger.exception("[Pool %d] update_pool_instances: laniakea failure: %s", pool.id, msg)
            return

        try:
            # first check status of pending spot requests
            requested = []
            for instance_id in instance_ids_by_region[region]:
                if instances_by_ids[instance_id].status_code == INSTANCE_STATE['requested']:
                    requested.append(instance_id)

            if requested:
                boto_results = cluster.check_spot_requests(requested, config.ec2_tags)

                for req_id, result in zip(requested, boto_results):
                    instance = instances_by_ids[req_id]

                    if isinstance(result, boto.ec2.instance.Instance):
                        logger.info("[Pool %d] spot request fulfilled %s -> %s", pool.id, req_id, result.id)

                        # spot request has been fulfilled
                        instance.hostname = result.public_dns_name
                        instance.ec2_instance_id = result.id
                        # state_code is a 16-bit value where the high byte is
                        # an opaque internal value and should be ignored.
                        instance.status_code = result.state_code & 255
                        instance.save()

                        # update local data structures to use the new instances instead
                        del instances_by_ids[req_id]
                        instances_by_ids[result.id] = instance
                        instance_ids_by_region[region].append(result.id)
                        # don't add it to instances_left yet to avoid race with adding tags

                        # Now that we saved the object into our database, mark the instance as updatable
                        # so our update code can pick it up and update it accordingly when it changes states
                        result.add_tag(SPOTMGR_TAG + "-Updatable", "1")

                        instances_created = True

                    # request object is returned in case request is closed/cancelled/failed
                    elif isinstance(result, boto.ec2.spotinstancerequest.SpotInstanceRequest):
                        if result.state in {"cancelled", "closed"}:
                            # this is normal, remove from DB and move on
                            logger.info("[Pool %d] spot request %s is %s", pool.id, req_id, result.state)
                            instances_by_ids[req_id].delete()
                        elif result.state in {"open", "active"}:
                            # this should not happen! warn and leave in DB in case it's fulfilled later
                            logger.warning("[Pool %d] Request %s is %s and %s.",
                                           pool.id,
                                           req_id,
                                           result.status.code,
                                           result.state)
                        else:  # state=failed
                            msg = "Request %s is %s and %s." % (req_id, result.status.code, result.state)

                            entry = PoolStatusEntry()
                            entry.type = POOL_STATUS_ENTRY_TYPE['unclassified']
                            entry.pool = pool
                            entry.msg = str(msg)
                            entry.isCritical = True
                            entry.save()

                            logger.error("[Pool %d] %s", pool.id, msg)
                            instances_by_ids[req_id].delete()

                    elif result is None:
                        logger.info("[Pool %d] spot request %s is still open", pool.pk, req_id)

                    else:
                        logger.warning("[Pool %d] spot request %s returned %s", pool.pk, req_id, type(result).__name__)

            boto_instances = cluster.find(filters={"tag:" + SPOTMGR_TAG + "-PoolId": str(pool.pk)})

            for boto_instance in boto_instances:
                # Store ID seen for debugging purposes
                debug_boto_instance_ids_seen.add(boto_instance.id)

                # state_code is a 16-bit value where the high byte is
                # an opaque internal value and should be ignored.
                state_code = boto_instance.state_code & 255

                if (SPOTMGR_TAG + "-Updatable" not in boto_instance.tags or
                        int(boto_instance.tags[SPOTMGR_TAG + "-Updatable"]) <= 0):
                    # The instance is not marked as updatable. We must not touch it because
                    # a spawning thread is still managing this instance. However, we must also
                    # remove this instance from the instances_left list if it's already in our
                    # database, because otherwise our code here would delete it from the database.
                    if boto_instance.id in instance_ids_by_region[region]:
                        instances_left.remove(instances_by_ids[boto_instance.id])
                    else:
                        debug_not_updatable_continue.add(boto_instance.id)
                    continue

                instance = None

                # Whenever we see an instance that is not in our instance list for that region,
                # make sure it's a terminated instance because we should never have a running
                # instance that matches the search above but is not in our database.
                if boto_instance.id not in instance_ids_by_region[region]:
                    if state_code not in [INSTANCE_STATE['shutting-down'], INSTANCE_STATE['terminated']]:

                        # As a last resort, try to find the instance in our database.
                        # If the instance was saved to our database between the entrance
                        # to this function and the search query sent to EC2, then the instance
                        # will not be in our instances list but returned by EC2. In this
                        # case, we try to load it directly from the database.
                        q = Instance.objects.filter(ec2_instance_id=boto_instance.id)
                        if q:
                            instance = q[0]
                            logger.error("[Pool %d] Instance with EC2 ID %s was reloaded from database.",
                                         pool.id, boto_instance.id)
                        else:
                            logger.error("[Pool %d] Instance with EC2 ID %s is not in our database.",
                                         pool.id, boto_instance.id)

                            # Terminate at this point, we run in an inconsistent state
                            assert(False)
                    debug_not_in_region[boto_instance.id] = state_code
                    continue

                instance = instances_by_ids[boto_instance.id]
                instances_left.remove(instance)

                # Check the status code and update if necessary
                if instance.status_code != state_code:
                    instance.status_code = state_code
                    instance.save()

                # If for some reason we don't have a hostname yet,
                # update it accordingly.
                if not instance.hostname:
                    instance.hostname = boto_instance.public_dns_name
                    instance.save()

        except (boto.exception.EC2ResponseError, boto.exception.BotoServerError, ssl.SSLError, socket.error) as msg:
            if "MaxSpotInstanceCountExceeded" in str(msg):
                logger.warning("[Pool %d] update_pool_instances: Maximum instance count exceeded for region %s",
                               pool.id, region)
                if not PoolStatusEntry.objects.filter(
                        pool=pool, type=POOL_STATUS_ENTRY_TYPE['max-spot-instance-count-exceeded']):
                    entry = PoolStatusEntry()
                    entry.pool = pool
                    entry.type = POOL_STATUS_ENTRY_TYPE['max-spot-instance-count-exceeded']
                    entry.msg = "Auto-selected region exceeded its maximum spot instance count."
                    entry.save()
            elif "Service Unavailable" in str(msg):
                logger.warning("[Pool %d] update_pool_instances: Temporary failure in region %s: %s",
                               pool.id, region, msg)
                entry = PoolStatusEntry()
                entry.pool = pool
                entry.type = POOL_STATUS_ENTRY_TYPE['temporary-failure']
                entry.msg = "Temporary failure occurred: %s" % msg
                entry.save()
            else:
                logger.exception("[Pool %d] update_pool_instances: boto failure: %s", pool.id, msg)
                entry = PoolStatusEntry()
                entry.type = POOL_STATUS_ENTRY_TYPE['unclassified']
                entry.pool = pool
                entry.isCritical = True
                entry.msg = "Unclassified error occurred: %s" % msg
                entry.save()
            return

    for instance in instances_left:
        reasons = []

        if instance.ec2_instance_id not in debug_boto_instance_ids_seen:
            reasons.append("no corresponding machine on EC2")

        if instance.ec2_instance_id in debug_not_updatable_continue:
            reasons.append("not updatable")

        if instance.ec2_instance_id in debug_not_in_region:
            reasons.append("has state code %s on EC2 but not in our region"
                           % debug_not_in_region[instance.ec2_instance_id])

        if not reasons:
            reasons.append("?")

        logger.info("[Pool %d] Deleting instance with EC2 ID %s from our database: %s",
                    pool.id, instance.ec2_instance_id, ", ".join(reasons))
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
