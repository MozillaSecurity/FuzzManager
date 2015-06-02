from django.core.management.base import NoArgsCommand
from ec2spotmanager.models import PoolConfiguration, InstancePool, Instance, INSTANCE_STATE,\
    PoolStatusEntry, POOL_STATUS_ENTRY_TYPE
from django.conf import settings
from ec2spotmanager.management.common import pid_lock_file
import time
import logging

from django.utils import timezone
from server.ec2spotmanager.models import PoolUptimeDetailedEntry
from django.db.models.query_utils import Q

stats_delta_secs = 60*30 # 30 minutes

class Command(NoArgsCommand):
    help = "Check the status of all bugs we have"
    @pid_lock_file("stats_daemon")
    def handle_noargs(self, **options):
        print(options)
        while True:
            self.check_instance_pools()
            time.sleep(60)
    
    def check_instance_pools(self):
        instance_pools = InstancePool.objects.all()
        
        # Process all instance pools
        for pool in instance_pools:
            if not pool.isEnabled:
                continue
            
            current_delta = timezone.datetime.now().date() - timezone.timedelta(seconds=stats_delta_secs)
            entries = PoolUptimeDetailedEntry.objects.filter(pool=pool, created__gte = current_delta)
            
            # We should never have more than one entry per time-delta
            assert(len(entries) < 2)
            
            if entries:
                current_delta_entry = entries[0]
            else:
                # Create a new entry
                current_delta_entry = PoolUptimeDetailedEntry()
                current_delta_entry.pool = pool
            
            current_delta_entry.target = pool.config.flatten().size
            
            actual = len(Instance.objects.filter(pool=pool).filter(Q(status_code=INSTANCE_STATE['pending'])| Q(status_code=INSTANCE_STATE['running'])))
            if current_delta_entry.actual == None or actual < current_delta_entry.actual:
                current_delta_entry.actual = actual
            
            # This will only save if necessary, i.e. if the entry already existed and the values
            # have not changed, this will not cause I/O on the database with Django >=1.5
            current_delta_entry.save()