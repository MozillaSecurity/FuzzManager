from django.core.management.base import NoArgsCommand
from ec2spotmanager.models import PoolConfiguration, InstancePool, Instance, INSTANCE_STATE,\
    PoolStatusEntry, POOL_STATUS_ENTRY_TYPE
from django.conf import settings
from ec2spotmanager.management.common import pid_lock_file
import time
import logging
import threading
from ec2spotmanager.common.prices import get_spot_prices, get_price_median

use_multiprocess_price_fetch = False
if use_multiprocess_price_fetch:
    from multiprocessing import Pool, cpu_count

from django.utils import timezone

from laniakea.laniakea import LaniakeaCommandLine
from laniakea.core.manager import Laniakea

import boto.ec2
import boto.exception

logger = logging.getLogger("ec2spotmanager")

class Command(NoArgsCommand):
    help = "Check the status of all bugs we have"
    @pid_lock_file("monitoring_daemon")
    def handle_noargs(self, **options):
        while True:
            self.check_instance_pools()
            time.sleep(10)
    
    def check_instance_pools(self):
        instance_pools = InstancePool.objects.all()

        # Process all instance pools
        for instance_pool in instance_pools:
            criticalPoolStatusEntries = PoolStatusEntry.objects.filter(pool = instance_pool, isCritical = True)
            
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
            
            instances = Instance.objects.filter(pool=instance_pool)
            
            for instance in instances:
                if instance.status_code in [INSTANCE_STATE['running'], INSTANCE_STATE['pending'], INSTANCE_STATE['requested']]:
                    instances_missing -= 1
                    running_instances.append(instance)
                elif instance.status_code in [INSTANCE_STATE['shutting-down'], INSTANCE_STATE['terminated']]: 
                    # The instance is no longer running, delete it from our database
                    logger.info("[Pool %d] Deleting terminated instance with EC2 ID %s from our database." % (instance_pool.id, instance.ec2_instance_id))
                    instance.delete()
                else:
                    logger.error("[Pool %d] Instance with EC2 ID %s has unexpected state code %d" % (instance_pool.id, instance.ec2_instance_id, instance.status_code))
                    # Terminate here for now so we can see which status code we are not handling properly
                    assert(False)
            
            # Continue working with the instances we have running
            instances = running_instances
                    
            if not instance_pool.isEnabled:
                if running_instances:
                    self.terminate_pool_instances(instance_pool, running_instances, config, terminateByPool=True)
                    
                    # Try to update our terminated instances as soon as possible. If EC2 needs longer than
                    # the here specified sleep time, the instances will be updated with the next iteration
                    # of this pool, allowing other actions to be processed in-between.
                    #time.sleep(2)
                    #self.update_pool_instances(instance_pool, config)
                continue
            
            if (not instance_pool.last_cycled) or instance_pool.last_cycled < timezone.now() - timezone.timedelta(seconds=config.cycle_interval):
                logger.info("[Pool %d] Needs to be cycled, terminating all instances..." % instance_pool.id)
                instance_pool.last_cycled = timezone.now()
                self.terminate_pool_instances(instance_pool, instances, config, terminateByPool=True)
                instance_pool.save()
                
                # Try to update our terminated instances as soon as possible. If EC2 needs longer than
                # the here specified sleep time, the instances will be updated with the next iteration
                # of this pool, allowing other actions to be processed in-between.
                #time.sleep(2)
                #self.update_pool_instances(instance_pool, config)
                logger.info("[Pool %d] Termination complete." % instance_pool.id)
            
            # Determine which instances need to be cycled
            #outdated_instances = instances.filter(created__lt = timezone.now() - timezone.timedelta(seconds=config.cycle_interval))
            
            # Terminate all instances that need cycling
            #for instance in outdated_instances:
            #    self.terminate_instance(instance, config)
            #    instances_missing += 1
            
            if instances_missing > 0:
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
        (region, zone, rejected) = self.get_best_region_zone(config)
        
        if not region:
            logger.warn("[Pool %d] No allowed region was cheap enough to spawn instances." % pool.id)
            
            entries = PoolStatusEntry.objects.filter(pool = pool, type = POOL_STATUS_ENTRY_TYPE['price-too-low'])
            if not entries:
                entry = PoolStatusEntry()
                entry.pool = pool
                entry.type = POOL_STATUS_ENTRY_TYPE['price-too-low']
                entry.msg = "No allowed region was cheap enough to spawn instances."
                for zone in rejected:
                    entry.msg += "\n%s at %s" % (zone, rejected[zone])
                entry.save()
            return
        
        logger.debug("[Pool %d] Using region %s with availability zone %s." % (pool.id, region, zone))
        
        instances = []
        
        # Create all our instances as pending, the async thread will update them once
        # they have been spawned.
        for i in range(0,count):
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
                raise RuntimeError("start_instances_async: Failed to compile userdata")
            
            images["default"]['user_data'] = userdata
            images["default"]['placement'] = zone
            images["default"]['count'] = count
    
            cluster = Laniakea(images)
            try:
                cluster.connect(region=region, aws_access_key_id=config.aws_access_key_id, aws_secret_access_key=config.aws_secret_access_key)
            except Exception as msg:
                logger.error("[Pool %d] %s: laniakea failure: %s" % (pool.id, "start_instances_async", msg))
                
                # Log this error to the pool status messages
                entry = PoolStatusEntry()
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
                (boto_instances, boto_pending) = cluster.create_spot(config.ec2_max_price, tags=config.ec2_tags, delete_on_termination=True, timeout=20*60)
                
                logger.info("[Pool %d] Successfully created %s instances, %s requests timed out and were canceled" % (pool.id, len(boto_instances), len(boto_pending)))
                
                assert (len(boto_instances) + len(boto_pending)) == len(instances) == count
                
                for i in range(0,len(boto_instances)):
                    instances[i].hostname = boto_instances[i].public_dns_name
                    instances[i].ec2_instance_id = boto_instances[i].id
                    instances[i].status_code = boto_instances[i].state_code
                    instances[i].save()
                    
                    assert(instances[i].ec2_instance_id != None)
                    
                    # Now that we saved the object into our database, mark the instance as updatable
                    # so our update code can pick it up and update it accordingly when it changes states 
                    boto_instances[i].add_tag("SpotManager-Updatable", "1")
                    
                if boto_pending:
                    for i in range(len(boto_instances),count):
                        # Delete instances belong to canceled spot requests
                        logger.info("[Pool %d] Deleting instance with id %s (belongs to canceled request)" % (pool.id, instances[i].pk))
                        instances[i].delete()
                
            except boto.exception.EC2ResponseError as msg:
                logger.error("[Pool %d] %s: boto failure: %s" % (pool.id, "start_instances_async", msg))
                return
        
        # TODO: We don't get any information back from the async method call here, but should handle failures!
        t = threading.Thread(target=start_instances_async, args = (pool, config, count, images, region, zone, instances))
        t.start()
        
    def terminate_pool_instances(self, pool, instances, config, terminateByPool=False):
        """ Terminate an instance with the given configuration """        
        instance_ids_by_region = self.get_instance_ids_by_region(instances)
        
        for region in instance_ids_by_region:
            cluster = Laniakea(None)
            try:
                cluster.connect(region=region, aws_access_key_id=config.aws_access_key_id, aws_secret_access_key=config.aws_secret_access_key)
            except Exception as msg:
                logger.error("[Pool %d] %s: laniakea failure: %s" % (pool.id, "terminate_pool_instances", msg))
                return None
        
            try:
                if terminateByPool:
                    boto_instances = cluster.find(filters={"tag:SpotManager-PoolId" : str(pool.pk)})
                    
                    # Data consistency checks
                    for boto_instance in boto_instances:
                        assert ((boto_instance.id in instance_ids_by_region[region])
                                or (boto_instance.state_code == INSTANCE_STATE['shutting-down'] 
                                or boto_instance.state_code == INSTANCE_STATE['terminated']))
                        
                    cluster.terminate(boto_instances)
                else:
                    logger.info("[Pool %d] Terminating %s instances in region %s" % (pool.id, len(instance_ids_by_region[region]),region))
                    cluster.terminate(cluster.find(instance_ids=instance_ids_by_region[region]))
            except boto.exception.EC2ResponseError as msg:
                logger.error("[Pool %d] %s: boto failure: %s" % (pool.id, "terminate_pool_instances", msg))
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
        
        for instance_id in instances_by_ids:
            if instance_id:
                instances_left.append(instances_by_ids[instance_id])
        
        for region in instance_ids_by_region:
            cluster = Laniakea(None)
            try:
                cluster.connect(region=region, aws_access_key_id=config.aws_access_key_id, aws_secret_access_key=config.aws_secret_access_key)
            except Exception as msg:
                logger.error("[Pool %d] %s: laniakea failure: %s" % (pool.id, "update_pool_instances", msg))
                return None
        
            try:
                boto_instances = cluster.find(filters={"tag:SpotManager-PoolId" : str(pool.pk), "tag:SpotManager-Updatable" : "1"})
                
                
                for boto_instance in boto_instances:
                    instance = None
                    
                    # Whenever we see an instance that is not in our instance list for that region,
                    # make sure it's a terminated instance because we should never have a running 
                    # instance that matches the search above but is not in our database.
                    if not boto_instance.id in instance_ids_by_region[region]:
                        if not ((boto_instance.state_code == INSTANCE_STATE['shutting-down'] 
                            or boto_instance.state_code == INSTANCE_STATE['terminated'])):
                            
                            # As a last resort, try to find the instance in our database.
                            # If the instance was saved to our database between the entrance
                            # to this function and the search query sent to EC2, then the instance
                            # will not be in our instances list but returned by EC2. In this
                            # case, we try to load it directly from the database.
                            q = Instance.objects.filter(ec2_instance_id = boto_instance.id)
                            if q:
                                instance = q[0]
                            else:
                                logger.error("[Pool %d] Instance with EC2 ID %s is not in our database." % (pool.id, boto_instance.id))
                                    
                                # Terminate at this point, we run in an inconsistent state
                                assert(False)
                            
                        continue
                    
                    if not instance:
                        instance = instances_by_ids[boto_instance.id]
                        instances_left.remove(instance)
                    
                    # Check the status code and update if necessary
                    if instance.status_code != boto_instance.state_code:
                        instance.status_code = boto_instance.state_code
                        instance.save()
                        
                    # If for some reason we don't have a hostname yet,
                    # update it accordingly.
                    if not instance.hostname:
                        instance.hostname = boto_instance.public_dns_name
                        instance.save()
                    
            except boto.exception.EC2ResponseError as msg:
                logger.error("%s: boto failure: %s" % ("update_pool_instances", msg))
                return 1
        
        if instances_left:
            for instance in instances_left:
                logger.info("[Pool %d] Deleting instance with EC2 ID %s from our database, has no corresponding machine on EC2." % (pool.id, instance.ec2_instance_id))
                instance.delete()
                    
