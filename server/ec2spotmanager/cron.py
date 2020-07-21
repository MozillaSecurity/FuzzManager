import datetime
import json
import logging
import celery
import redis
from django.conf import settings
from django.db.models.query_utils import Q
from django.utils import timezone
from celeryconf import app
from .CloudProvider.CloudProvider import INSTANCE_STATE, PROVIDERS, CloudProvider
from server.utils import RedisLock


LOG = logging.getLogger("ec2spotmanager")


STATS_DELTA_SECS = 60 * 15  # 30 minutes
STATS_TOTAL_DETAILED = 24  # How many hours the detailed statistics should include
STATS_TOTAL_ACCUMULATED = 30  # How many days should we keep accumulated statistics

# How long check_instance_pools lock should remain valid. If the task takes longer than this to complete, the lock will
# be invalidated and another task allowed to run.
CHECK_POOL_LOCK_EXPIRY = 30 * 60


@app.task(ignore_result=True)
def update_stats():
    from .models import PoolUptimeDetailedEntry, PoolUptimeAccumulatedEntry, InstancePool, Instance

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
def _release_lock(lock_key):
    cache = redis.StrictRedis.from_url(settings.REDIS_URL)
    lock = RedisLock(cache, "ec2spotmanager:check_instance_pools", unique_id=lock_key)
    if not lock.release():
        LOG.warning('Lock ec2spotmanager:check_instance_pools(%s) was already expired.', lock_key)


@app.task(ignore_result=True)
def check_instance_pools():
    """EC2SpotManager daemon.

    - checks all instance pools
    - spawns and monitors spot requests asynchronously
    - cycles pools as required
    """
    from .models import InstancePool, Instance
    from .tasks import check_and_resize_pool, cycle_and_terminate_disabled, terminate_instances, update_instances, \
        update_requests

    # This is the Celery "canvas" for how tasks are linked together.
    #
    #                         START
    #                           |
    #       ===================================================
    #                  |
    #           ===============                         \
    #               |                                    \
    #             update                                  \
    #              spot    ... one per pool within region  \
    #              reqs                                     |
    #               |                                      /
    #           ===============                           /
    #                  |                                  \
    #                  |                                   \  ... one per provider+region
    #               reconcile                              /
    #             DB and provider                         /
    #              (across pools)                         \
    #                  |                                   \
    #                  |                                    |
    #            terminate instances                       /
    #            for disabled pools                       /
    #            + pools needing cycle                   /
    #               (across pools)                      /
    #                  |
    #                  |
    #       ===================================================
    #                           |
    #                           |
    #       ===================================================
    #                          |                        \
    #                         /\         /\              \
    #                        /  \       /  \              \
    #                       /pool\     /pool\              \
    #                    Y / too  \ N / too  \ N            |
    #                   |--\small /-->\large /-----|       /
    #                   |   \    /     \    /      |      /
    #                   |    \  /       \  /       |      \
    #                   |     \/         \/        |       \  ... one per enabled pool
    #                   |                 |Y       |       /
    #                   |                 |        |      /
    #             spawn instances     queue for    |      \
    #               in cheapest         batch      |       \
    #             provider+region    termination   |        |
    #                   |                 |        |       /
    #                   |                 |        |      /
    #                   |                 |        |     /
    #                   |                 |        |    /
    #       ===================================================
    #                           |
    #                           |
    #                       ===========
    #                           |
    #                        terminate
    #                      any instances      ... one per provider+region
    #                   from pool downsizing
    #                     (across pools)
    #                           |
    #                       ===========
    #                           |
    #                          DONE
    #
    cache = redis.StrictRedis.from_url(settings.REDIS_URL)
    lock = RedisLock(cache, "ec2spotmanager:check_instance_pools")

    lock_key = lock.acquire(lock_expiry=CHECK_POOL_LOCK_EXPIRY)
    if lock_key is None:
        LOG.warning('Another EC2SpotManager update still in progress, exiting.')
        return

    try:
        groups = {}
        for pool in InstancePool.objects.all():
            cfg = pool.config.flatten()
            for provider in PROVIDERS:
                cloud_provider = CloudProvider.get_instance(provider)
                if cloud_provider.config_supported(cfg):
                    for region in cloud_provider.get_allowed_regions(cfg):
                        groups.setdefault((provider, region), set()).add(pool.pk)
                # also look at running instances. it could be that this pool was just edited to exclude a provider,
                # but we still must manage active instances running there.
                for region in Instance.objects.filter(pool=pool, provider=provider).values_list('region', flat=True):
                    groups.setdefault((provider, region), set()).add(pool.pk)

        provider_parallel = []
        for (provider, region), pools in groups.items():
            provider_parallel.append(
                celery.chain(celery.group([update_requests.si(provider, region, pool) for pool in pools]),
                             update_instances.si(provider, region),
                             cycle_and_terminate_disabled.si(provider, region)))

        pool_parallel = []
        for pool in InstancePool.objects.filter(isEnabled=True):
            pool_parallel.append(check_and_resize_pool.si(pool.pk))

        celery.chain(
            celery.group(provider_parallel),
            celery.chord(
                pool_parallel,
                terminate_instances.s()
            ),
            _release_lock.si(lock_key)  # release on chain success
        ).on_error(_release_lock.si(lock_key))()  # release on chain failure

    except Exception:  # pylint: disable=broad-except
        try:
            if not lock.release():  # release on error in this function
                LOG.warning('Lock %s was already expired.', lock_key)
        except Exception:  # pylint: disable=broad-except
            LOG.exception("Ignoring exception raised while releasing lock.")
        finally:
            raise


@app.task(ignore_result=True)
def update_prices():
    """Periodically refresh spot price history and store it in redis to be consumed when spot instances are created.

    Prices are stored in redis, with keys like:
        'ec2spot:price:{instance-type}'
    and values as JSON objects {region: {az: [prices]}} like:
        '{"us-east-1": {"us-east-1a": [0.08000, ...]}}'
    """
    from .models import PoolConfiguration

    for provider in PROVIDERS:
        regions = set()
        cloud_provider = CloudProvider.get_instance(provider)
        for cfg in PoolConfiguration.objects.all():
            config = cfg.flatten()
            if cloud_provider.config_supported(config):
                allowed_regions = cloud_provider.get_allowed_regions(config)
                if allowed_regions:
                    regions |= set(allowed_regions)
        if not regions:
            continue

        prices = {}
        for region in regions:
            for instance_type, price_data in cloud_provider.get_prices_per_region(region).items():
                prices.setdefault(instance_type, {})
                prices[instance_type].update(price_data)

        now = timezone.now()
        expires = now + datetime.timedelta(hours=12)  # how long this data is valid (if not replaced)
        # use pipeline() so everything is in 1 transaction per provider.
        cache = redis.StrictRedis.from_url(settings.REDIS_URL).pipeline()
        for instance_type in prices:
            key = provider + ':price:' + instance_type
            cache.delete(key)
            cache.set(key, json.dumps(prices[instance_type], separators=(',', ':')))
            cache.expireat(key, expires)
        cache.execute()  # commit to redis
