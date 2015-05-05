from django.core.management.base import NoArgsCommand
from ec2spotmanager.models import PoolConfiguration, InstancePool, Instance, INSTANCE_STATE,\
    PoolStatusEntry
from django.conf import settings
from ec2spotmanager.management.common import pid_lock_file
import warnings
import datetime
import time
import logging
import threading

use_multiprocess_price_fetch = False
if use_multiprocess_price_fetch:
    from multiprocessing import Pool, cpu_count

from django.utils import timezone

from laniakea.laniakea import LaniakeaCommandLine
from laniakea.core.manager import Laniakea
import boto.ec2
import boto.exception

# This function must be defined at the module level so it can be pickled
# by the multiprocessing module when calling this asynchronously.
def get_spot_price_per_region(region_name, aws_key_id, aws_secret_key, instance_type):
    '''Gets spot prices of the specified region and instance type'''
    now = datetime.datetime.now()
    start = now - datetime.timedelta(hours=6)
    r = boto.ec2.connect_to_region(region_name, 
                                   aws_access_key_id=aws_key_id,
                                   aws_secret_access_key=aws_secret_key
                                   ).get_spot_price_history(
                                        start_time=start.isoformat(),
                                        instance_type=instance_type,
                                        product_description="Linux/UNIX"
                                        ) #TODO: Make configurable
    return r

class Command(NoArgsCommand):
    help = "Check the status of all bugs we have"
    @pid_lock_file
    def handle_noargs(self, **options):
        while True:
            self.check_instance_pools()
            time.sleep(10)
    
    def check_instance_pools(self):
        instance_pools = InstancePool.objects.all()
        
        # Process all instance pools
        for instance_pool in instance_pools:
            poolEntries = PoolStatusEntry.objects.filter(pool = instance_pool)
            
            if poolEntries:
                print("Instance Pool has unchecked errors, ignoring...")
                continue
            
            config = instance_pool.config.flatten()
            instances = Instance.objects.filter(pool=instance_pool)
            
            instances_missing = config.size
            running_instances = []
            
            self.update_pool_instances(instance_pool, instances, config)
            for instance in instances:
                if instance.status_code == INSTANCE_STATE['running'] or instance.status_code == INSTANCE_STATE['pending']:
                    instances_missing -= 1
                    running_instances.append(instance)
                else:
                    # The instance is no longer running, delete it from our database
                    instance.delete()
            
            # Continue working with the instances we have running
            instances = running_instances
            
            if (not instance_pool.last_cycled) or instance_pool.last_cycled < timezone.now() - timezone.timedelta(seconds=config.cycle_interval):
                print("[Main] Pool needs to be cycled, terminating all instances...")
                instance_pool.last_cycled = timezone.now()
                self.terminate_pool_instances(instance_pool, instances, config, terminateByPool=True)
                instance_pool.save()
                self.update_pool_instances(instance_pool, instances, config)
                print("[Main] Pool termination complete.")
            
            # Determine which instances need to be cycled
            #outdated_instances = instances.filter(created__lt = timezone.now() - timezone.timedelta(seconds=config.cycle_interval))
            
            # Terminate all instances that need cycling
            #for instance in outdated_instances:
            #    self.terminate_instance(instance, config)
            #    instances_missing += 1
            
            if instances_missing > 0:
                print("[Main] Pool needs %s more instances, starting..." % instances_missing)
                self.start_pool_instances(instance_pool, config, count=instances_missing)
            elif instances_missing < 0:
                # Select the oldest instances we have running and terminate
                # them so we meet the size limitation again.
                print("[Main] Pool has %s instances over limit, terminating..." % -instances_missing)
                instances = Instance.objects.filter(pool=instance_pool).order_by('created')[:-instances_missing]
                self.terminate_pool_instances(instance_pool, instances, config)
            else:
                print("[Main] Pool size ok.")
                
    def get_best_region_zone(self, config):
        def get_price_median(data):
            sdata = sorted(data)
            n = len(sdata)
            if not n % 2:
                return (sdata[n / 2] + sdata[n / 2 - 1]) / 2.0
            return sdata[n / 2]
        
        if use_multiprocess_price_fetch:
            pool = Pool(cpu_count())
            
        results = []
        for region in config.ec2_allowed_regions:
            if use_multiprocess_price_fetch:
                f = pool.apply_async(get_spot_price_per_region, [region, config.aws_access_key_id, config.aws_secret_access_key, config.ec2_instance_type])
            else:
                f = get_spot_price_per_region(region, config.aws_access_key_id, config.aws_secret_access_key, config.ec2_instance_type)
            results.append(f)

        prices = {}
        for result in results:
            if use_multiprocess_price_fetch:
                result = result.get()
            for entry in result:
                if not entry.region.name in prices:
                    prices[entry.region.name] = {}
                    
                zone = entry.availability_zone
                
                if not zone in prices[entry.region.name]:
                    prices[entry.region.name][zone] = []
                    
                prices[entry.region.name][zone].append(entry.price)
                
        # Calculate median values for all availability zones and best zone/price
        best_zone = None
        best_region = None
        best_median = None
        for region in prices:
            for zone in prices[region]:
                # Do not consider a zone/region combination that has a current
                # price higher than the maximum price we are willing to pay,
                # even if the median would end up being lower than our maximum.
                if prices[region][zone][-1] > config.ec2_max_price:
                    continue
                
                median = get_price_median(prices[region][zone])
                if best_median == None or best_median > median:
                    best_median = median
                    best_zone = zone
                    best_region = region
        
        return (best_region, best_zone)
    
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
        (region, zone) = self.get_best_region_zone(config)
        print("Using region %s with availability zone %s" % (region,zone))
        
        instances = []
        
        # Create all our instances as pending, the async thread will update them once
        # they have been spawned.
        for i in range(0,count):
            instance = Instance()
            instance.ec2_region = region
            instance.status_code = INSTANCE_STATE["pending"]
            instance.pool = pool
            instance.save()
            instances.append(instance)
        
        # This method will run async to spawn our machines
        def start_instances_async(pool, config, count, images, region, zone, instances):
            userdata = LaniakeaCommandLine.handle_import_tags(config.ec2_userdata)
            userdata = LaniakeaCommandLine.handle_tags(userdata, config.ec2_userdata_macros)
            if not userdata:
                raise RuntimeError("start_instance: Failed to compile userdata")
            
            images["default"]['user_data'] = userdata
            images["default"]['placement'] = zone
            images["default"]['count'] = count
    
            cluster = Laniakea(images)
            try:
                cluster.connect(region=region, aws_access_key_id=config.aws_access_key_id, aws_secret_access_key=config.aws_secret_access_key)
            except Exception as msg:
                logging.error("%s: laniakea failure: %s" % ("start_instances_async", msg))
                
                # Log this error to the pool status messages
                entry = PoolStatusEntry()
                entry.pool = pool
                entry.msg = str(msg)
                entry.save()
                
                # Delete all pending instances as we failed to create them
                for instance in instances:
                    instance.delete()
                    
                return
            
            config.ec2_tags['SpotManager-PoolId'] = str(pool.pk)
    
            try:
                print("Creating %s instances" % count)
                (boto_instances, boto_pending) = cluster.create_spot(config.ec2_max_price, tags=config.ec2_tags, delete_on_termination=True, timeout=20*60)
                
                print("Successfully created %s instances, %s requests timed out and were canceled" % (len(boto_instances), len(boto_pending)))
                
                assert (len(boto_instances) + len(boto_pending)) == len(instances) == count
                
                for i in range(0,len(boto_instances)):
                    instances[i].hostname = boto_instances[i].public_dns_name
                    instances[i].ec2_instance_id = boto_instances[i].id
                    instances[i].status_code = boto_instances[i].state_code
                    instances[i].save()
                    
                if boto_pending:
                    for i in range(len(boto_instances),len(boto_pending)):
                        # Delete instances belong to canceled spot requests
                        print("Deleting instance with id %s (belongs to canceled request)" % instances[i].pk)
                        instances[i].delete()
                
            except boto.exception.EC2ResponseError as msg:
                logging.error("%s: boto failure: %s" % ("start_instances_async", msg))
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
                logging.error("%s: laniakea failure: %s" % ("terminate_pool_instances", msg))
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
                    print("Terminating %s instances in region %s" % (len(instance_ids_by_region[region]),region))
                    cluster.terminate(cluster.find(instance_ids=instance_ids_by_region[region]))
            except boto.exception.EC2ResponseError as msg:
                logging.error("%s: boto failure: %s" % ("terminate_pool_instances", msg))
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
    
    def update_pool_instances(self, pool, instances, config):
        """ Check the state of the instances in a pool and update it in the database """
        instance_ids_by_region = self.get_instance_ids_by_region(instances)
        instances_by_ids = self.get_instances_by_ids(instances)
        
        for region in instance_ids_by_region:
            cluster = Laniakea(None)
            try:
                cluster.connect(region=region, aws_access_key_id=config.aws_access_key_id, aws_secret_access_key=config.aws_secret_access_key)
            except Exception as msg:
                logging.error("%s: laniakea failure: %s" % ("update_pool_instances", msg))
                return None
        
            try:
                #cluster.find(instance_ids=instance_ids_by_region[region])
                boto_instances = cluster.find(filters={"tag:SpotManager-PoolId" : str(pool.pk)})
                
                for boto_instance in boto_instances:
                    # Whenever we see an instance that is not in our instance list for that region,
                    # make sure it's a terminated instance because we should never have running instance
                    #
                    # We must however not perform this check if we still have pending instances.
                    # In this case, the thread that is monitoring the pending instances must first
                    # redeclare them with their proper id in the database before we perform *any*
                    # updates on it. Otherwise, parallel save operations on the instance object
                    # might lead to inconsistent states of the database model    
                    if not boto_instance.id in instance_ids_by_region[region]:
                        if not None in instance_ids_by_region:
                            assert (boto_instance.state_code == INSTANCE_STATE['shutting-down'] 
                                or boto_instance.state_code == INSTANCE_STATE['terminated'])
                            
                        continue
                        
                    instance = instances_by_ids[boto_instance.id]
                    
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
                logging.error("%s: boto failure: %s" % ("update_pool_instances", msg))
                return 1
            
                    
