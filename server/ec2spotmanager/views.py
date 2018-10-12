import json
from operator import attrgetter
from chartjs.colors import next_color
from chartjs.views.base import JSONView
from django.conf import settings
from django.core.exceptions import SuspiciousOperation
from django.core.files.base import ContentFile
from django.db.models.aggregates import Count
from django.http.response import Http404  # noqa
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.timezone import now, timedelta
import fasteners
import redis
from rest_framework import status
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from rest_framework.response import Response
from rest_framework.views import APIView
from server.auth import CheckAppPermission
from server.views import deny_restricted_users
from .models import InstancePool, PoolConfiguration, Instance, PoolStatusEntry
from .models import PoolUptimeDetailedEntry, PoolUptimeAccumulatedEntry
from .serializers import MachineStatusSerializer
from .CloudProvider.CloudProvider import INSTANCE_STATE, INSTANCE_STATE_CODE, PROVIDERS, CloudProvider


def renderError(request, err):
    return render(request, 'error.html', {'error_message': err})


@deny_restricted_users
def index(request):
    return redirect('ec2spotmanager:pools')


@deny_restricted_users
def pools(request):
    filters = {}
    isSearch = True

    entries = InstancePool.objects.annotate(size=Count('instance')).order_by('config__name')

    # These are all keys that are allowed for exact filtering
    exactFilterKeys = [
        "config__name",
        "config__name__contains",
        "isEnabled",
    ]

    for key in exactFilterKeys:
        if key in request.GET:
            filters[key] = request.GET[key]

    # If we don't have any filters up to this point, don't consider it a search
    if not filters:
        isSearch = False

    entries = entries.filter(**filters)
    for entry in entries:
        entry.msgs = PoolStatusEntry.objects.filter(pool=entry).order_by('-created')

    for pool in entries:
        pool.instance_requested_count = sum(instance.size for instance in Instance.objects.filter(
            pool=pool, status_code=INSTANCE_STATE['requested']))
        pool.instance_running_count = sum(instance.size for instance in Instance.objects.filter(
            pool=pool, status_code=INSTANCE_STATE['running']))
        if pool.size <= pool.instance_running_count:
            pool.size_label = 'success'
        elif pool.size == 0:
            pool.size_label = 'danger'
        else:
            pool.size_label = 'warning'

    data = {
        'isSearch': isSearch,
        'poollist': entries,
    }

    return render(request, 'pools/index.html', data)


@deny_restricted_users
def viewPool(request, poolid):
    pool = get_object_or_404(InstancePool, pk=poolid)
    instances = Instance.objects.filter(pool=poolid)

    for instance in instances:
        if instance.status_code in INSTANCE_STATE_CODE:
            instance.status_code_text = INSTANCE_STATE_CODE[instance.status_code]
        else:
            instance.status_code_text = "Unknown (%s)" % instance.status_code

    cyclic = pool.config.isCyclic()

    last_config = pool.config
    last_config.children = []

    while not cyclic and last_config.parent is not None:
        last_config.parent.children = [last_config]
        last_config = last_config.parent

    parent_config = last_config

    missing = None
    if not cyclic:
        # Figure out if any parameters are missing
        missing = pool.config.getMissingParameters()

    data = {'pool': pool, 'parent_config': parent_config, 'instances': instances, 'config_params_missing': missing,
            'config_cyclic': cyclic}

    return render(request, 'pools/view.html', data)


@deny_restricted_users
def viewPoolPrices(request, poolid):
    cache = redis.StrictRedis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.REDIS_DB)
    cloud_provider = CloudProvider.get_instance(PROVIDERS[0])

    pool = get_object_or_404(InstancePool, pk=poolid)
    config = pool.config.flatten()
    cores_per_instance = cloud_provider.get_cores_per_instance()
    allowed_regions = set(cloud_provider.get_allowed_regions(config))
    zones = set()
    latest_price_by_zone = {}

    for instance_type in cloud_provider.get_instance_types(config):
        prices = cache.get('%s:price:%s' % (cloud_provider.get_name(), instance_type))
        if prices is None:
            continue
        prices = json.loads(prices)
        for region in prices:
            if region not in allowed_regions:
                continue
            for zone in prices[region]:
                zones.add(zone)
                latest_price_by_zone[zone] = min(latest_price_by_zone.get(zone, 9999),
                                                 prices[region][zone][0] / cores_per_instance[instance_type])

    prices = []
    for zone in sorted(zones):
        prices.append((zone, latest_price_by_zone[zone]))

    return render(request, 'pools/prices.html', {'prices': prices})


@deny_restricted_users
def disablePool(request, poolid):
    pool = get_object_or_404(InstancePool, pk=poolid)

    if not pool.isEnabled:
        return render(request, 'pools/error.html', {'error_message': 'That pool is already disabled.'})

    if request.method == 'POST':
        pool.isEnabled = False
        pool.save()
        return redirect('ec2spotmanager:poolview', poolid=pool.pk)
    elif request.method == 'GET':
        pool.instance_running_count = Instance.objects.filter(pool=pool, status_code=INSTANCE_STATE['running']).count()
        return render(request, 'pools/disable.html', {'pool': pool})
    else:
        raise SuspiciousOperation


@deny_restricted_users
def enablePool(request, poolid):
    pool = get_object_or_404(InstancePool, pk=poolid)

    # Safety check: Figure out if any parameters are missing
    # or if the configuration is cyclic, even though the link
    # to this function should not be reachable in the UI at
    # this point already.
    cyclic = pool.config.isCyclic()
    if cyclic:
        return render(request, 'pools/error.html', {'error_message': 'Pool configuration is cyclic.'})

    missing = pool.config.getMissingParameters()
    if missing:
        return render(request, 'pools/error.html', {'error_message': 'Pool is missing configuration parameters.'})

    if pool.isEnabled:
        return render(request, 'pools/error.html', {'error_message': 'That pool is already enabled.'})

    if request.method == 'POST':
        pool.isEnabled = True
        pool.last_cycled = None
        pool.save()
        return redirect('ec2spotmanager:poolview', poolid=pool.pk)
    elif request.method == 'GET':
        return render(request, 'pools/enable.html', {'pool': pool, 'coreCount': pool.config.flatten().size})
    else:
        raise SuspiciousOperation


@deny_restricted_users
def forceCyclePool(request, poolid):
    pool = get_object_or_404(InstancePool, pk=poolid)

    if not pool.isEnabled:
        return render(request, 'pools/error.html', {'error_message': 'Pool is disabled.'})

    if request.method == 'POST':
        pool.last_cycled = None
        pool.save()
        return redirect('ec2spotmanager:poolview', poolid=pool.pk)
    elif request.method == 'GET':
        pool.instance_running_count = Instance.objects.filter(pool=pool, status_code=INSTANCE_STATE['running']).count()
        return render(request, 'pools/cycle.html', {'pool': pool})
    else:
        raise SuspiciousOperation


@deny_restricted_users
def forceCyclePoolsByConfig(request, configid):
    config = get_object_or_404(PoolConfiguration, pk=configid)

    def recurse_get_dependent_configurations(config):
        config_pks = [config.pk]
        configs = PoolConfiguration.objects.filter(parent=config)

        for config in configs:
            config_pks.extend(recurse_get_dependent_configurations(config))

        return config_pks

    if request.method == 'POST':
        pool_pks = request.POST.getlist('poolids')
        InstancePool.objects.filter(pk__in=pool_pks, isEnabled=True).update(last_cycled=None)
        return redirect('ec2spotmanager:pools')
    elif request.method == 'GET':
        # Recursively enumerate all configurations directly or indirectly depending on this one
        config_pks = recurse_get_dependent_configurations(config)

        # Get all pools depending on our configurations
        pools = InstancePool.objects.filter(config__pk__in=config_pks, isEnabled=True)

        for pool in pools:
            pool.instance_running_count = Instance.objects.filter(pool=pool, status_code=INSTANCE_STATE['running']) \
                .count()

        return render(request, 'config/cycle.html', {'config': config, 'pools': pools})
    else:
        raise SuspiciousOperation


@deny_restricted_users
def createPool(request):
    if request.method == 'POST':
        pool = InstancePool()
        config = get_object_or_404(PoolConfiguration, pk=int(request.POST['config']))
        pool.config = config
        pool.save()
        return redirect('ec2spotmanager:poolview', poolid=pool.pk)
    elif request.method == 'GET':
        configurations = PoolConfiguration.objects.all()
        return render(request, 'pools/create.html', {'configurations': configurations})
    else:
        raise SuspiciousOperation


@deny_restricted_users
def viewConfigs(request):
    configs = PoolConfiguration.objects.all()
    roots = configs.filter(parent=None)

    def add_children(node):
        node.children = []
        children = configs.filter(parent=node)
        for child in children:
            node.children.append(child)
            add_children(child)

    for root in roots:
        add_children(root)

    data = {'roots': roots}

    return render(request, 'config/index.html', data)


@deny_restricted_users
def viewConfig(request, configid):
    config = get_object_or_404(PoolConfiguration, pk=configid)

    config.deserializeFields()

    return render(request, 'config/view.html', {'config': config})


def __handleConfigPOST(request, config):
    if int(request.POST['parent']) < 0:
        config.parent = None
    else:
        # TODO: Cyclic config check
        config.parent = get_object_or_404(PoolConfiguration, pk=int(request.POST['parent']))

    config.name = request.POST['name']

    if request.POST['size']:
        config.size = int(request.POST['size'])
    else:
        config.size = None

    if request.POST['cycle_interval']:
        config.cycle_interval = int(request.POST['cycle_interval'])
    else:
        config.cycle_interval = None

    if request.POST['ec2_key_name']:
        config.ec2_key_name = request.POST['ec2_key_name']
    else:
        config.ec2_key_name = None

    if request.POST['ec2_image_name']:
        config.ec2_image_name = request.POST['ec2_image_name']
    else:
        config.ec2_image_name = None

    if request.POST['ec2_max_price']:
        config.ec2_max_price = float(request.POST['ec2_max_price'])
    else:
        config.ec2_max_price = None

    if request.POST['ec2_allowed_regions']:
        config.ec2_allowed_regions_list = [x.strip() for x in request.POST['ec2_allowed_regions'].split(',')]
    else:
        config.allowed_regions_list = None
    config.allowed_regions_override = request.POST.get('allowed_regions_override', 'off') == 'on'

    if request.POST['ec2_security_groups']:
        config.ec2_security_groups_list = [x.strip() for x in request.POST['ec2_security_groups'].split(',')]
    else:
        config.ec2_security_groups_list = None
    config.ec2_security_groups_override = request.POST.get('ec2_security_groups_override', 'off') == 'on'

    if request.POST['ec2_instance_types']:
        config.ec2_instance_types_list = [x.strip() for x in request.POST['ec2_instance_types'].split(',')]
    else:
        config.ec2_instance_types_list = None
    config.ec2_instance_types_override = request.POST.get('ec2_instance_types_override', 'off') == 'on'

    if request.POST['userdata_macros']:
        config.userdata_macros_dict = dict(
            y.split('=', 1) for y in [x.strip() for x in request.POST['userdata_macros'].split(',')])
    else:
        config.userdata_macros_dict = None
    config.userdata_macros_override = request.POST.get('userdata_macros_override', 'off') == 'on'

    if request.POST['ec2_tags']:
        config.ec2_tags_dict = dict(y.split('=', 1) for y in [x.strip() for x in request.POST['ec2_tags'].split(',')])
    else:

        config.ec2_tags_dict = None
    config.ec2_tags_override = request.POST.get('ec2_tags_override', 'off') == 'on'

    if request.POST['ec2_raw_config']:
        config.ec2_raw_config_dict = dict(
            y.split('=', 1) for y in [x.strip() for x in request.POST['ec2_raw_config'].split(',')])
    else:
        config.ec2_raw_config_dict = None
    config.ec2_raw_config_override = request.POST.get('ec2_raw_config_override', 'off') == 'on'

    # Ensure we have a primary key before attempting to store files
    config.save()

    if request.POST['userdata']:
        if not config.userdata_file.name:
            config.userdata_file.save("default.sh", ContentFile(""))
        config.userdata = request.POST['userdata']
        if request.POST.get('userdata_ff', 'unix') == 'unix':
            config.userdata = config.userdata.replace('\r\n', '\n')
        config.storeTestAndSave()
    else:
        if config.userdata_file:
            # Forcing test saving with userdata unset will clean the file
            config.userdata = None
            config.storeTestAndSave()

    return redirect('ec2spotmanager:configview', configid=config.pk)


@deny_restricted_users
def createConfig(request):
    if request.method == 'POST':
        config = PoolConfiguration()
        return __handleConfigPOST(request, config)
    elif request.method == 'GET':
        configurations = PoolConfiguration.objects.all()

        if "clone" in request.GET:
            config = get_object_or_404(PoolConfiguration, pk=int(request.GET["clone"]))
            config.name = "%s (Cloned)" % config.name
            config.pk = None
            clone = True
        else:
            config = PoolConfiguration()
            clone = False

        config.deserializeFields()

        data = {'clone': clone,
                'config': config,
                'configurations': configurations,
                'edit': False,
                'userdata_ff': 'unix'}
        return render(request, 'config/edit.html', data)
    else:
        raise SuspiciousOperation


@deny_restricted_users
def editConfig(request, configid):
    config = get_object_or_404(PoolConfiguration, pk=configid)
    config.deserializeFields()

    if request.method == 'POST':
        return __handleConfigPOST(request, config)
    elif request.method == 'GET':
        configurations = PoolConfiguration.objects.all()
        data = {'config': config,
                'configurations': configurations,
                'edit': True,
                'userdata_ff': 'dos' if (b'\r\n' in (config.userdata or b'')) else 'unix'}
        return render(request, 'config/edit.html', data)
    else:
        raise SuspiciousOperation


@deny_restricted_users
def deletePool(request, poolid):
    pool = get_object_or_404(InstancePool, pk=poolid)

    if pool.isEnabled:
        return render(request, 'pools/error.html', {
            'error_message': 'That pool is still enabled, you must disable it first.'})

    instances = Instance.objects.filter(pool=poolid)
    if instances:
        return render(request, 'pools/error.html', {
            'error_message': ('That pool still has instances associated with it. '
                              'Please wait for their termination first.')})

    if request.method == 'POST':
        lock = fasteners.InterProcessLock('/tmp/ec2spotmanager.pool%s.lck' % poolid)

        if not lock.acquire(blocking=False):
            return render(request, 'pools/error.html', {
                'error_message': ('That pool is currently being updated. Please try again.')})

        try:
            pool.delete()
        finally:
            lock.release()

        return redirect('ec2spotmanager:pools')

    elif request.method == 'GET':
        return render(request, 'pools/delete.html', {'entry': pool})
    else:
        raise SuspiciousOperation


@deny_restricted_users
def deletePoolMsg(request, msgid):
    entry = get_object_or_404(PoolStatusEntry, pk=msgid)
    if request.method == 'POST':
        entry.delete()
        return redirect('ec2spotmanager:pools')
    elif request.method == 'GET':
        return render(request, 'pools/messages/delete.html', {'entry': entry})
    else:
        raise SuspiciousOperation


@deny_restricted_users
def deleteConfig(request, configid):
    config = get_object_or_404(PoolConfiguration, pk=configid)

    pools = InstancePool.objects.filter(config=config)
    for pool in pools:
        if pool.isEnabled:
            return render(request, 'pools/error.html', {
                'error_message': 'That configuration is still used by one or more (enabled) instance pools.'})

        instances = Instance.objects.filter(pool=pool)
        if instances:
            return render(request, 'pools/error.html', {
                'error_message': ('A pool using this configuration still has instances associated with it. '
                                  'Please wait for their termination first.')})

    if PoolConfiguration.objects.filter(parent=config):
        return render(request, 'pools/error.html', {
            'error_message': 'That configuration is still referenced by one or more other configurations.'})

    if request.method == 'POST':
        pools.delete()
        config.delete()
        return redirect('ec2spotmanager:configs')
    elif request.method == 'GET':
        return render(request, 'config/delete.html', {'entry': config, 'pools': pools})
    else:
        raise SuspiciousOperation


class UptimeChartViewDetailed(JSONView):
    authentication_classes = (SessionAuthentication,)  # noqa

    def get_context_data(self, **kwargs):
        context = super(UptimeChartViewDetailed, self).get_context_data(**kwargs)
        pool = InstancePool.objects.get(pk=int(kwargs['poolid']))
        pool.flat_config = pool.config.flatten()

        latest = now() - timedelta(hours=24)
        entries = PoolUptimeDetailedEntry.objects.filter(pool=pool, created__gt=latest).order_by('created')

        context.update({
            'labels': self.get_labels(pool, entries),
            'datasets': self.get_datasets(pool, entries),
            'options': self.get_options(pool, entries),
        })
        return context

    def get_colors(self):
        return next_color()

    def get_data_colors(self, entries):
        colors = []
        red = (204, 0, 0)
        yellow = (255, 204, 0)
        green = (0, 163, 0)

        for point in entries:
            if point.actual == point.target:
                colors.append("rgba(%d, %d, %d, 1)" % green)
            elif not point.actual:
                colors.append("rgba(%d, %d, %d, 1)" % red)
            else:
                colors.append("rgba(%d, %d, %d, 1)" % yellow)

        return colors

    def get_options(self, pool, entries):
        if entries:
            scaleSteps = max(entries, key=attrgetter('target')).target + 1
        else:
            # Default to the current pool size if we have no entries at all
            scaleSteps = pool.flat_config.size + 1
        return {
            'scaleOverride': True,
            'scaleSteps': scaleSteps,
            'scaleStepWidth': 1,
            'scaleStartValue': -1,
            'barValueSpacing': 0,
            'barShowStroke': False,
        }

    def get_datasets(self, pool, entries):
        datasets = []
        color_generator = self.get_colors()
        color = tuple(next(color_generator))

        data = [x.actual for x in entries]
        dataset = {
            'fillColor': self.get_data_colors(entries),
            # 'highlightFill': "rgba(84,255,159,0.2)",
            'strokeColor': "rgba(%d, %d, %d, 1)" % color,
            'pointColor': "rgba(%d, %d, %d, 1)" % color,
            'pointStrokeColor': "#fff",
            'data': data
        }

        datasets.append(dataset)
        return datasets

    def get_labels(self, pool, entries):
        return [x.created.strftime("%H:%M") for x in entries]


class UptimeChartViewAccumulated(JSONView):
    authentication_classes = (SessionAuthentication,)  # noqa

    def get_context_data(self, **kwargs):
        context = super(UptimeChartViewAccumulated, self).get_context_data(**kwargs)
        pool = InstancePool.objects.get(pk=int(kwargs['poolid']))
        pool.flat_config = pool.config.flatten()

        latest = now() - timedelta(days=30)  # TODO: Use settings instead of hardcoding
        entries = PoolUptimeAccumulatedEntry.objects.filter(pool=pool, created__gt=latest).order_by('created')

        context.update({
            'labels': self.get_labels(pool, entries),
            'datasets': self.get_datasets(pool, entries),
            'options': self.get_options(pool, entries),
        })
        return context

    def get_colors(self):
        return next_color()

    def get_data_colors(self, entries):
        colors = []
        red = (204, 0, 0)
        orange = (255, 128, 0)
        yellow = (255, 204, 0)
        green = (0, 163, 0)

        for point in entries:
            if point.uptime_percentage >= 95.00:
                colors.append("rgba(%d, %d, %d, 1)" % green)
            elif point.uptime_percentage <= 25.00:
                colors.append("rgba(%d, %d, %d, 1)" % red)
            elif point.uptime_percentage <= 50.00:
                colors.append("rgba(%d, %d, %d, 1)" % orange)
            else:
                colors.append("rgba(%d, %d, %d, 1)" % yellow)

        return colors

    def get_options(self, pool, entries):
        # Scale to 100% but use 110 so the red bar is actually visible
        scaleSteps = 11
        return {
            'scaleOverride': True,
            'scaleSteps': scaleSteps,
            'scaleStepWidth': 10,
            'scaleStartValue': -10,
            'scaleLabel': '<%=value%>%',
            'tooltipTemplate': '<%if (label){%><%=label%>: <%}%><%= value%>%',
            'barValueSpacing': 0,
            'barShowStroke': False,
        }

    def get_datasets(self, pool, entries):
        datasets = []
        color_generator = self.get_colors()
        color = tuple(next(color_generator))

        data = [x.uptime_percentage for x in entries]
        dataset = {
            'fillColor': self.get_data_colors(entries),
            # 'highlightFill': "rgba(84,255,159,0.2)",
            'strokeColor': "rgba(%d, %d, %d, 1)" % color,
            'pointColor': "rgba(%d, %d, %d, 1)" % color,
            'pointStrokeColor': "#fff",
            'data': data
        }

        datasets.append(dataset)
        return datasets

    def get_labels(self, pool, entries):
        return [x.created.strftime("%b %d") for x in entries]


class MachineStatusViewSet(APIView):
    authentication_classes = (TokenAuthentication,)  # noqa

    def get(self, request, *args, **kwargs):
        result = {}
        response = Response(result, status=status.HTTP_200_OK)
        return response

    def post(self, request, *args, **kwargs):
        if 'client' not in request.data:
            return Response({"error": '"client" is required.'}, status=status.HTTP_400_BAD_REQUEST)

        instance = get_object_or_404(Instance, hostname=request.data['client'])
        serializer = MachineStatusSerializer(instance=instance, partial=True, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PoolCycleView(APIView):
    authentication_classes = (TokenAuthentication,)  # noqa
    permission_classes = (CheckAppPermission,)

    def post(self, request, poolid, format=None):
        pool = get_object_or_404(InstancePool, pk=poolid)

        if not pool.isEnabled:
            return Response({"error": 'Pool is disabled.'}, status=status.HTTP_406_NOT_ACCEPTABLE)

        pool.last_cycled = None
        pool.save()

        return Response({}, status=status.HTTP_200_OK)


class PoolEnableView(APIView):
    authentication_classes = (TokenAuthentication,)  # noqa
    permission_classes = (CheckAppPermission,)

    def post(self, request, poolid, format=None):
        pool = get_object_or_404(InstancePool, pk=poolid)

        if pool.isEnabled:
            return Response({"error": 'Pool is already enabled.'}, status=status.HTTP_406_NOT_ACCEPTABLE)

        pool.last_cycled = None
        pool.isEnabled = True
        pool.save()

        return Response({}, status=status.HTTP_200_OK)


class PoolDisableView(APIView):
    authentication_classes = (TokenAuthentication,)  # noqa
    permission_classes = (CheckAppPermission,)

    def post(self, request, poolid, format=None):
        pool = get_object_or_404(InstancePool, pk=poolid)

        if not pool.isEnabled:
            return Response({"error": 'Pool is already disabled.'}, status=status.HTTP_406_NOT_ACCEPTABLE)

        pool.isEnabled = False
        pool.save()

        return Response({}, status=status.HTTP_200_OK)
