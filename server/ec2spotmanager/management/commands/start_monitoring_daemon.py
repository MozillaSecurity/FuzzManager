import boto.ec2
import boto.exception
from django.conf import settings
from django.core.management.base import NoArgsCommand
from django.utils import timezone
import logging
import signal
import socket
import ssl
import threading
import time

from ec2spotmanager.common.prices import get_spot_prices, get_price_median
from ec2spotmanager.management.common import pid_lock_file
from ec2spotmanager.models import PoolConfiguration, InstancePool, Instance, INSTANCE_STATE, \
    PoolStatusEntry, POOL_STATUS_ENTRY_TYPE
from laniakea.core.manager import Laniakea
from laniakea.laniakea import LaniakeaCommandLine


use_multiprocess_price_fetch = False
if use_multiprocess_price_fetch:
    from multiprocessing import Pool, cpu_count

logger = logging.getLogger("ec2spotmanager")

# A global variable to memorize our current instance starting threads per pool
# We use this variable mainly to ensure that we have one start thread per
# pool only, as the start_pool_instances_async method is not necessarily
# thread-safe when used on the same pool twice.
async_start_threads_by_poolid = {}

# Global variable for indicating shutdown through InterruptHandler
pending_shutdown = False
def handle_interrupt(signal, frame):
    global pending_shutdown
    logger.info("Shutdown initiated...")
    pending_shutdown = True

class Command(NoArgsCommand):
    help = "Check the status of all bugs we have"
    @pid_lock_file("monitoring_daemon")
    def handle_noargs(self, **options):
        signal.signal(signal.SIGINT, handle_interrupt)

        self.check_instance_pools(initialCheck=True)
        while True:
            self.check_instance_pools()

            if pending_shutdown and not async_start_threads_by_poolid:
                logger.info("Shutdown complete.")
                return 0

            time.sleep(10)

    def check_instance_pools(self, initialCheck=False):
        # Check all start threads
        finished_start_thread_poolids = [id for id in async_start_threads_by_poolid if not async_start_threads_by_poolid[id].isAlive()]
        for id in finished_start_thread_poolids:
            del async_start_threads_by_poolid[id]

        # Process all instance pools
        instance_pools = InstancePool.objects.all()
        for instance_pool in instance_pools:
            criticalPoolStatusEntries = PoolStatusEntry.objects.filter(pool=instance_pool, isCritical=True)

            if criticalPoolStatusEntries:
                continue

            if instance_pool.config.isCyclic() or instance_pool.config.getMissingParameters():
                entry = PoolStatusEntry()
                entry.pool = instance_pool
                entry.isCritical = True
                entry.type = POOL_STATUS_ENTRY_TYPE['config-error']
                entry.msg = "Configuration error."
                entry.save()
                continue

            config = instance_pool.config.flatten()

            instances_missing = config.size
            running_instances = []

            self.update_pool_instances(instance_pool, config)

            # On our initial check, we only do everything up to the pool update
            # to ensure that for every pool, the pool update can run successfully.
            if initialCheck:
                continue

            instances = Instance.objects.filter(pool=instance_pool)

            for instance in instances:
                instance_status_code_fixed = False
                if instance.status_code >= 256:
                    logger.warning("[Pool %d] Instance with EC2 ID %s has weird state code %d, attempting to fix..." % (instance_pool.id, instance.ec2_instance_id, instance.status_code))
                    instance.status_code -= 256
                    instance_status_code_fixed = True

                if instance.status_code in [INSTANCE_STATE['running'], INSTANCE_STATE['pending'], INSTANCE_STATE['requested']]:
                    instances_missing -= 1
                    running_instances.append(instance)
                elif instance.status_code in [INSTANCE_STATE['shutting-down'], INSTANCE_STATE['terminated']]:
                    # The instance is no longer running, delete it from our database
                    logger.info("[Pool %d] Deleting terminated instance with EC2 ID %s from our database." % (instance_pool.id, instance.ec2_instance_id))
                    instance.delete()
                else:
                    if instance_status_code_fixed:
                        # Restore original status code for error reporting
                        instance.status_code += 256

                    logger.error("[Pool %d] Instance with EC2 ID %s has unexpected state code %d" % (instance_pool.id, instance.ec2_instance_id, instance.status_code))
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
                    self.terminate_pool_instances(instance_pool, running_instances, config, terminateByPool=True)

                    # Try to update our terminated instances as soon as possible. If EC2 needs longer than
                    # the here specified sleep time, the instances will be updated with the next iteration
                    # of this pool, allowing other actions to be processed in-between.
                    # time.sleep(2)
                    # self.update_pool_instances(instance_pool, config)
                continue

            if (not instance_pool.last_cycled) or instance_pool.last_cycled < timezone.now() - timezone.timedelta(seconds=config.cycle_interval):
                if pending_shutdown:
                    logger.info("[Pool %d] Shutdown pending, skipping pool cycle..." % instance_pool.id)
                else:
                    logger.info("[Pool %d] Needs to be cycled, terminating all instances..." % instance_pool.id)
                    instance_pool.last_cycled = timezone.now()
                    self.terminate_pool_instances(instance_pool, instances, config, terminateByPool=True)
                    instance_pool.save()

                    logger.info("[Pool %d] Termination complete." % instance_pool.id)

            if instances_missing > 0:
                if pending_shutdown:
                    logger.info("[Pool %d] Shutdown pending, not starting further instances..." % instance_pool.id)
                elif instance_pool.id in async_start_threads_by_poolid:
                    logger.debug("[Pool %d] Already has a start thread running, not starting further instances..." % instance_pool.id)
                else:
                    logger.info("[Pool %d] Needs %s more instances, starting..." % (instance_pool.id, instances_missing))
                    self.start_pool_instances(instance_pool, config, count=instances_missing)
            elif instances_missing < 0:
                # Select the oldest instances we have running and terminate
                # them so we meet the size limitation again.
                logger.info("[Pool %d] Has %s instances over limit, terminating..." % (instance_pool.id, -instances_missing))
                instances = Instance.objects.filter(pool=instance_pool).order_by('created')[:-instances_missing]
                self.terminate_pool_instances(instance_pool, instances, config)
            else:
                logger.debug("[Pool %d] Size is ok." % instance_pool.id)

    def get_best_region_zone(self, config):
        prices = get_spot_prices(config.ec2_allowed_regions, config.aws_access_key_id, config.aws_secret_access_key, config.ec2_instance_type)

        # Calculate median values for all availability zones and best zone/price
        best_zone = None
        best_region = None
        best_median = None
        rejected_prices = {}
        for region in prices:
            for zone in prices[region]:
                # Do not consider a zone/region combination that has a current
                # price higher than the maximum price we are willing to pay,
                # even if the median would end up being lower than our maximum.
                if prices[region][zone][0] > config.ec2_max_price:
                    rejected_prices[zone] = prices[region][zone][0]
                    continue

                median = get_price_median(prices[region][zone])
                if best_median == None or best_median > median:
                    best_median = median
                    best_zone = zone
                    best_region = region

        return (best_region, best_zone, rejected_prices)

    def create_laniakea_images(self, config):
        images = { "default" : {} }

        # These are the configuration keys we want to put into the target configuration
        # without further preprocessing, except for the adjustment of the key name itself.
        keys = [
            'ec2_key_name',
            'ec2_image_name',
            'ec2_instance_type',
            'ec2_security_groups',
        ]

        for key in keys:
            lkey = key.replace("ec2_", "", 1)
            images["default"][lkey] = config[key]

        if config.ec2_raw_config:
            images["default"].update(config.ec2_raw_config)

        return images

    def start_pool_instances(self, pool, config, count=1):
        """ Start an instance with the given configuration """

        images = self.create_laniakea_images(config)

        # Figure out where to put our instances
        try:
            (region, zone, rejected) = self.get_best_region_zone(config)
        except (boto.exception.EC2ResponseError, boto.exception.BotoServerError, ssl.SSLError, socket.error) as msg:
            # In case of temporary failures here, we will retry again in the next cycle
            logger.warn("[Pool %d] Failed to aquire spot instance prices: %s." % (pool.id, msg))
            return
        except (RuntimeError) as msg:
            logger.error("[Pool %d] Failed to compile userdata." % pool.id)
            entry = PoolStatusEntry()
            entry.type = POOL_STATUS_ENTRY_TYPE['config-error']
            entry.pool = pool
            entry.isCritical = True
            entry.msg = "Configuration error: %s" % msg
            entry.save()
            return

        priceLowEntries = PoolStatusEntry.objects.filter(pool=pool, type=POOL_STATUS_ENTRY_TYPE['price-too-low'])

        if not region:
            logger.warn("[Pool %d] No allowed region was cheap enough to spawn instances." % pool.id)

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

        logger.debug("[Pool %d] Using region %s with availability zone %s." % (pool.id, region, zone))

        instances = []

        # Create all our instances as pending, the async thread will update them once
        # they have been spawned.
        for i in range(0, count):
            instance = Instance()
            instance.ec2_region = region
            instance.ec2_zone = zone
            instance.status_code = INSTANCE_STATE["requested"]
            instance.pool = pool
            instance.save()
            instances.append(instance)

        # This method will run async to spawn our machines
        def start_instances_async(pool, config, count, images, region, zone, instances):
            userdata = LaniakeaCommandLine.handle_import_tags(config.ec2_userdata)
            userdata = LaniakeaCommandLine.handle_tags(userdata, config.ec2_userdata_macros)
            if not userdata:
                logger.error("[Pool %d] Failed to compile userdata." % pool.id)

                entry = PoolStatusEntry()
                entry.type = POOL_STATUS_ENTRY_TYPE['config-error']
                entry.pool = pool
                entry.isCritical = True
                entry.msg = "Configuration error: Failed to compile userdata"
                entry.save()

                for instance in instances:
                    instance.delete()

                raise RuntimeError("start_instances_async: Failed to compile userdata")

            images["default"]['user_data'] = userdata
            images["default"]['placement'] = zone
            images["default"]['count'] = count

            cluster = Laniakea(images)
            try:
                cluster.connect(region=region, aws_access_key_id=config.aws_access_key_id, aws_secret_access_key=config.aws_secret_access_key)
            except Exception as msg:
                logger.exception("[Pool %d] %s: laniakea failure: %s" % (pool.id, "start_instances_async", msg))

                # Log this error to the pool status messages
                entry = PoolStatusEntry()
                entry.type = 0
                entry.pool = pool
                entry.msg = str(msg)
                entry.isCritical = True
                entry.save()

                # Delete all pending instances as we failed to create them
                for instance in instances:
                    instance.delete()

                return

            config.ec2_tags['SpotManager-PoolId'] = str(pool.pk)

            try:
                logger.info("[Pool %d] Creating %s instances..." % (pool.id, count))
                boto_instances = cluster.create_spot(config.ec2_max_price, tags=config.ec2_tags, delete_on_termination=True, timeout=20 * 60)
                canceled_requests = count - len(boto_instances)

                logger.info("[Pool %d] Successfully created %s instances, %s requests timed out and were canceled" % (pool.id, len(boto_instances), canceled_requests))

                for i in range(0, len(boto_instances)):
                    instances[i].hostname = boto_instances[i].public_dns_name
                    instances[i].ec2_instance_id = boto_instances[i].id
                    # state_code is a 16-bit value where the high byte is
                    # an opaque internal value and should be ignored.
                    instances[i].status_code = boto_instances[i].state_code & 255
                    instances[i].save()

                    assert(instances[i].ec2_instance_id != None)

                    # Now that we saved the object into our database, mark the instance as updatable
                    # so our update code can pick it up and update it accordingly when it changes states
                    boto_instances[i].add_tag("SpotManager-Updatable", "1")

                if canceled_requests > 0:
                    for i in range(len(boto_instances), count):
                        # Delete instances belong to canceled spot requests
                        logger.info("[Pool %d] Deleting instance with id %s (belongs to canceled request)" % (pool.id, instances[i].pk))
                        instances[i].delete()

                # Delete certain warnings we might have created earlier that no longer apply

                # If we ever exceeded the maximum spot instance count, we can clear
                # the warning now because we obviously succeeded in starting some instances.
                PoolStatusEntry.objects.filter(pool=pool, type=POOL_STATUS_ENTRY_TYPE['max-spot-instance-count-exceeded']).delete()

                # The same holds for temporary failures of any sort
                PoolStatusEntry.objects.filter(pool=pool, type=POOL_STATUS_ENTRY_TYPE['temporary-failure']).delete()

                # Do not delete unclassified errors here for now, so the user can see them.

            except (boto.exception.EC2ResponseError, boto.exception.BotoServerError, ssl.SSLError, socket.error) as msg:
                if "MaxSpotInstanceCountExceeded" in str(msg):
                    logger.warning("[Pool %d] Maximum instance count exceeded for region %s" % (pool.id, region))
                    if not PoolStatusEntry.objects.filter(pool=pool, type=POOL_STATUS_ENTRY_TYPE['max-spot-instance-count-exceeded']):
                        entry = PoolStatusEntry()
                        entry.pool = pool
                        entry.type = POOL_STATUS_ENTRY_TYPE['max-spot-instance-count-exceeded']
                        entry.msg = "Auto-selected region exceeded its maximum spot instance count."
                        entry.save()
                elif "Service Unavailable" in str(msg):
                    logger.warning("[Pool %d] Temporary failure in region %s: %s" % (pool.id, region, msg))
                    entry = PoolStatusEntry()
                    entry.pool = pool
                    entry.type = POOL_STATUS_ENTRY_TYPE['temporary-failure']
                    entry.msg = "Temporary failure occurred: %s" % msg
                    entry.save()
                else:
                    logger.exception("[Pool %d] %s: boto failure: %s" % (pool.id, "start_instances_async", msg))
                    entry = PoolStatusEntry()
                    entry.type = 0
                    entry.pool = pool
                    entry.isCritical = True
                    entry.msg = "Unclassified error occurred: %s" % msg
                    entry.save()

                # Delete all pending instances, assuming that an exception from laniakea
                # means that all instance requests failed.
                for instance in instances:
                    instance.delete()

                return

        # TODO: We don't get any information back from the async method call here, but should handle failures!
        t = threading.Thread(target=start_instances_async, args=(pool, config, count, images, region, zone, instances))
        async_start_threads_by_poolid[pool.id] = t
        t.start()

    def terminate_pool_instances(self, pool, instances, config, terminateByPool=False):
        """ Terminate an instance with the given configuration """
        instance_ids_by_region = self.get_instance_ids_by_region(instances)

        for region in instance_ids_by_region:
            cluster = Laniakea(None)
            try:
                cluster.connect(region=region, aws_access_key_id=config.aws_access_key_id, aws_secret_access_key=config.aws_secret_access_key)
            except Exception as msg:
                # Log this error to the pool status messages
                entry = PoolStatusEntry()
                entry.type = 0
                entry.pool = pool
                entry.msg = str(msg)
                entry.isCritical = True
                entry.save()

                logger.exception("[Pool %d] %s: laniakea failure: %s" % (pool.id, "terminate_pool_instances", msg))
                return None

            try:
                if terminateByPool:
                    boto_instances = cluster.find(filters={"tag:SpotManager-PoolId" : str(pool.pk)})

                    # Data consistency checks
                    for boto_instance in boto_instances:
                        # state_code is a 16-bit value where the high byte is
                        # an opaque internal value and should be ignored.
                        state_code = boto_instance.state_code & 255
                        if not ((boto_instance.id in instance_ids_by_region[region])
                                or (state_code == INSTANCE_STATE['shutting-down']
                                or state_code == INSTANCE_STATE['terminated'])):
                            logger.error("[Pool %d] Instance with EC2 ID %s (status %d) is not in region list for region %s" % (pool.id, boto_instance.id, state_code, region))

                    cluster.terminate(boto_instances)
                else:
                    logger.info("[Pool %d] Terminating %s instances in region %s" % (pool.id, len(instance_ids_by_region[region]), region))
                    cluster.terminate(cluster.find(instance_ids=instance_ids_by_region[region]))
            except (boto.exception.EC2ResponseError, boto.exception.BotoServerError, ssl.SSLError, socket.error) as msg:
                logger.exception("[Pool %d] %s: boto failure: %s" % (pool.id, "terminate_pool_instances", msg))
                return 1

    def get_instance_ids_by_region(self, instances):
        instance_ids_by_region = {}

        for instance in instances:
            if not instance.ec2_region in instance_ids_by_region:
                instance_ids_by_region[instance.ec2_region] = []
            instance_ids_by_region[instance.ec2_region].append(instance.ec2_instance_id)

        return instance_ids_by_region

    def get_instances_by_ids(self, instances):
        instances_by_ids = {}
        for instance in instances:
            instances_by_ids[instance.ec2_instance_id] = instance
        return instances_by_ids

    def update_pool_instances(self, pool, config):
        """ Check the state of the instances in a pool and update it in the database """
        instances = Instance.objects.filter(pool=pool)
        instance_ids_by_region = self.get_instance_ids_by_region(instances)
        instances_by_ids = self.get_instances_by_ids(instances)
        instances_left = []

        debug_boto_instance_ids_seen = set()
        debug_not_updatable_continue = set()
        debug_not_in_region = {}


        for instance_id in instances_by_ids:
            if instance_id:
                instances_left.append(instances_by_ids[instance_id])

        for region in instance_ids_by_region:
            cluster = Laniakea(None)
            try:
                cluster.connect(region=region, aws_access_key_id=config.aws_access_key_id, aws_secret_access_key=config.aws_secret_access_key)
            except Exception as msg:
                # Log this error to the pool status messages
                entry = PoolStatusEntry()
                entry.type = 0
                entry.pool = pool
                entry.msg = str(msg)
                entry.isCritical = True
                entry.save()

                logger.exception("[Pool %d] %s: laniakea failure: %s" % (pool.id, "update_pool_instances", msg))
                return None

            try:
                boto_instances = cluster.find(filters={"tag:SpotManager-PoolId" : str(pool.pk)})

                for boto_instance in boto_instances:
                    # Store ID seen for debugging purposes
                    debug_boto_instance_ids_seen.add(boto_instance.id)

                    # state_code is a 16-bit value where the high byte is
                    # an opaque internal value and should be ignored.
                    state_code = boto_instance.state_code & 255

                    if "SpotManager-Updatable" not in boto_instance.tags or int(boto_instance.tags["SpotManager-Updatable"]) <= 0:
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
                    if not boto_instance.id in instance_ids_by_region[region]:
                        if not ((state_code == INSTANCE_STATE['shutting-down']
                            or state_code == INSTANCE_STATE['terminated'])):

                            # As a last resort, try to find the instance in our database.
                            # If the instance was saved to our database between the entrance
                            # to this function and the search query sent to EC2, then the instance
                            # will not be in our instances list but returned by EC2. In this
                            # case, we try to load it directly from the database.
                            q = Instance.objects.filter(ec2_instance_id=boto_instance.id)
                            if q:
                                instance = q[0]
                                logger.error("[Pool %d] Instance with EC2 ID %s was reloaded from database." % (pool.id, boto_instance.id))
                            else:
                                logger.error("[Pool %d] Instance with EC2 ID %s is not in our database." % (pool.id, boto_instance.id))

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
                logger.exception("%s: boto failure: %s" % ("update_pool_instances", msg))
                return 1

        if instances_left:
            for instance in instances_left:
                if not instance.ec2_instance_id in debug_boto_instance_ids_seen:
                    logger.info("[Pool %d] Deleting instance with EC2 ID %s from our database, has no corresponding machine on EC2." % (pool.id, instance.ec2_instance_id))

                if instance.ec2_instance_id in debug_not_updatable_continue:
                    logger.error("[Pool %d] Deleting instance with EC2 ID %s from our database because it is not updatable but not in our region." % (pool.id, instance.ec2_instance_id))

                if instance.ec2_instance_id in debug_not_in_region:
                    logger.info("[Pool %d] Deleting instance with EC2 ID %s from our database, has state code %s on EC2" % (pool.id, instance.ec2_instance_id, debug_not_in_region[instance.ec2_instance_id]))

                logger.info("[Pool %d] Deleting instance with EC2 ID %s from our database." % (pool.id, instance.ec2_instance_id))
                instance.delete()

