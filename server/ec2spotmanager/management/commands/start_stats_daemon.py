from django.core.management.base import NoArgsCommand
from ec2spotmanager.models import PoolUptimeDetailedEntry, PoolUptimeAccumulatedEntry, InstancePool, Instance, INSTANCE_STATE
from django.conf import settings
from ec2spotmanager.management.common import pid_lock_file
import time
import logging

from django.utils import timezone
from django.db.models.query_utils import Q

stats_delta_secs = 60*30 # 30 minutes
stats_total_detailed = 24 # How many hours the detailed statistics should include
stats_total_accumulated = 30 # How many days should we keep accumulated statistics

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
            
            current_delta = timezone.datetime.now() - timezone.timedelta(seconds=stats_delta_secs)
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
            
            # Now check if we need to aggregate some of the detail entries we have
            entries = PoolUptimeDetailedEntry.objects.filter(pool=pool).order_by('created')
            
            n = len(entries) - (stats_total_detailed*60)/stats_delta_secs
            if n > 0:
                # We need to aggregate some entries
                entriesAggr = entries[0:n]
                
                for entry in entriesAggr:
                    # Figure out if we have an aggregated entry already with the same date
                    day_entries = PoolUptimeAccumulatedEntry.objects.filter(pool=pool, created__contains=entry.created.date())
                    
                    # We should never have more than one entry per day
                    assert(len(day_entries) < 2)
                    
                    if day_entries:
                        day_entry = day_entries[0]
                    else:
                        day_entry = PoolUptimeAccumulatedEntry()
                        day_entry.created = entry.created
                        day_entry.uptime_percentage = 0.0
                    
                    entry_percentage = round((float(entry.actual) / entry.target) * 100, 2)
                    
                    new_uptime_percentage = ((day_entry.uptime_percentage * day_entry.accumulated_count) + entry_percentage) / (day_entry.accumulated_count + 1)
                    
                    day_entry.uptime_percentage = new_uptime_percentage
                    day_entry.accumulated_count = day_entry.accumulated_count + 1
                    day_entry.save()
                    
                    # We can now delete our entry
                    entry.delete()
            
            # Finally check if we need to expire some accumulated entries
            entries = PoolUptimeAccumulatedEntry.objects.filter(pool=pool).order_by('created')
            
            n = len(entries) - stats_total_accumulated
            if n > 0:
                entries[0:n].delete()