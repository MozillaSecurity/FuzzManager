import datetime
import json

import redis
from django.conf import settings
from django.db.models.query_utils import Q
from django.utils import timezone

from celeryconf import app


STATS_DELTA_SECS = 60 * 15  # 30 minutes
STATS_TOTAL_DETAILED = 24  # How many hours the detailed statistics should include
STATS_TOTAL_ACCUMULATED = 30  # How many days should we keep accumulated statistics


@app.task
def update_stats():
    from .models import PoolUptimeDetailedEntry, PoolUptimeAccumulatedEntry, InstancePool, Instance, INSTANCE_STATE

    instance_pools = InstancePool.objects.all()

    # Process all instance pools
    for pool in instance_pools:
        if not pool.isEnabled:
            continue

        current_delta = timezone.now() - datetime.timedelta(seconds=STATS_DELTA_SECS)
        entries = PoolUptimeDetailedEntry.objects.filter(pool=pool, created__gte=current_delta)

        # We should never have more than one entry per time-delta
        assert entries.count() < 2

        if entries.count():
            current_delta_entry = entries[0]
        else:
            # Create a new entry
            current_delta_entry = PoolUptimeDetailedEntry()
            current_delta_entry.pool = pool

        current_delta_entry.target = pool.config.flatten().size

        actual = Instance.objects.filter(pool=pool).filter(Q(status_code=INSTANCE_STATE['pending']) |
                                                           Q(status_code=INSTANCE_STATE['running'])).count()
        if current_delta_entry.actual is None or actual < current_delta_entry.actual:
            current_delta_entry.actual = actual

        # This will only save if necessary, i.e. if the entry already existed and the values
        # have not changed, this will not cause I/O on the database with Django >=1.5
        current_delta_entry.save()

        # Now check if we need to aggregate some of the detail entries we have
        entries = PoolUptimeDetailedEntry.objects.filter(pool=pool).order_by('created')

        n = entries.count() - (STATS_TOTAL_DETAILED * 60 * 60) / STATS_DELTA_SECS
        if n > 0:
            # We need to aggregate some entries
            entriesAggr = entries[:n]

            for entry in entriesAggr:
                # Figure out if we have an aggregated entry already with the same date
                created = entry.created.date()
                day_entries = PoolUptimeAccumulatedEntry.objects.filter(pool=pool).filter(
                    created__year=created.year, created__month=created.month, created__day=created.day)

                # We should never have more than one entry per day
                assert day_entries.count() < 2

                if day_entries.count():
                    day_entry = day_entries[0]
                else:
                    day_entry = PoolUptimeAccumulatedEntry()
                    day_entry.pool = pool
                    day_entry.created = entry.created
                    day_entry.uptime_percentage = 0.0

                entry_percentage = 100
                if entry.target > 0:
                    entry_percentage = (float(entry.actual) / entry.target) * 100

                new_uptime_percentage = ((float(day_entry.uptime_percentage) * day_entry.accumulated_count) +
                                         entry_percentage) / (day_entry.accumulated_count + 1)

                day_entry.uptime_percentage = new_uptime_percentage
                day_entry.accumulated_count = day_entry.accumulated_count + 1
                day_entry.save()

                # We can now delete our entry
                entry.delete()

        # Finally check if we need to expire some accumulated entries
        entries = PoolUptimeAccumulatedEntry.objects.filter(pool=pool).order_by('created')

        n = entries.count() - STATS_TOTAL_ACCUMULATED
        if n > 0:
            for entry in entries[:n]:
                entry.delete()


@app.task
def check_instance_pools():
    from .models import InstancePool
    from .tasks import check_instance_pool
    for instance_pool in InstancePool.objects.all():
        check_instance_pool.delay(instance_pool.id)


@app.task
def update_spot_prices():
    """Periodically refresh spot price history and store it in redis to be consumed when spot instances are created.

    Prices are stored in redis, with keys like:
        'ec2spot:price:{instance-type}'
    and values as JSON objects {region: {az: [prices]}} like:
        '{"us-east-1": {"us-east-1a": [0.08000, ...]}}'
    """
    from .common.ec2 import REGIONS
    from .common.prices import get_spot_prices

    now = timezone.now()
    expires = now + datetime.timedelta(hours=3)  # how long this data is valid (if not replaced)

    prices = get_spot_prices(REGIONS,
                             getattr(settings, 'AWS_ACCESS_KEY_ID', None),
                             getattr(settings, 'AWS_SECRET_ACCESS_KEY', None))

    # use pipeline() so everything is in 1 transaction
    cache = redis.StrictRedis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.REDIS_DB).pipeline()
    for instance_type in prices:
        key = 'ec2spot:price:' + instance_type
        cache.delete(key)
        cache.set(key, json.dumps(prices[instance_type]))
        cache.expireat(key, expires)
    cache.execute()  # commit to redis
