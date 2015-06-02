from django.shortcuts import render, redirect, get_object_or_404
from ec2spotmanager.models import InstancePool, PoolConfiguration, Instance,\
    INSTANCE_STATE_CODE, PoolStatusEntry
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import logout
from django.db.models.aggregates import Count
from django.core.exceptions import SuspiciousOperation
from django.conf import settings

import os
import errno

from ec2spotmanager.common.prices import get_spot_prices
from django.core.files.base import ContentFile
from chartjs.views.base import JSONView
from chartjs.colors import next_color
from django.utils.timezone import now, timedelta
from ec2spotmanager.models import PoolUptimeDetailedEntry
from operator import attrgetter

def renderError(request, err):
    return render(request, 'error.html', { 'error_message' : err })

def logout_view(request):
    logout(request)
    return redirect('ec2spotmanager:index')

@login_required(login_url='/login/')
def index(request):
    return redirect('ec2spotmanager:pools')

@login_required(login_url='/login/')
def pools(request):
    filters = {}
    isSearch = True
    
    entries = InstancePool.objects.annotate(size=Count('instance')).order_by('-id')
    
    #(user, created) = User.objects.get_or_create(user = request.user)
    #defaultToolsFilter = user.defaultToolsFilter.all()
    #if defaultToolsFilter:
    #    entries = entries.filter(reduce(operator.or_, [Q(("tool",x)) for x in defaultToolsFilter]))
    
    # These are all keys that are allowed for exact filtering
    exactFilterKeys = [
                       "config__name",
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
    
    # Figure out if our daemons are running
    def checkDaemon(daemon_name):
        daemonPidFile = os.path.join(settings.BASE_DIR, "%s.pid" % daemon_name)
        daemonRunning = False
        try:
            with open(daemonPidFile, 'r') as f:
                daemonRunning = True
                pid = int(f.read())
                try:
                    os.kill(pid, 0)
                except OSError as e:
                    if e.errno == errno.ESRCH:
                        daemonRunning = False
                    elif e.errno == errno.EPERM:
                        daemonRunning = True
        except IOError:
            pass
        return daemonRunning
                
    data = { 
            'isSearch' : isSearch, 
            'poollist' : entries, 
            'machineDaemonRunning' : checkDaemon("monitoring_daemon"), 
            'statsDaemonRunning' : checkDaemon("stats_daemon"), 
            }
    
    return render(request, 'pools/index.html', data)

@login_required(login_url='/login/')
def viewPool(request, poolid):
    pool = get_object_or_404(InstancePool, pk=poolid)
    instances = Instance.objects.filter(pool=poolid)
    
    for instance in instances:
        instance.status_code_text = INSTANCE_STATE_CODE[instance.status_code]
        
    cyclic = pool.config.isCyclic()
    
    last_config = pool.config
    last_config.children = []
    
    while not cyclic and last_config.parent != None:
        last_config.parent.children = [ last_config ]
        last_config = last_config.parent
    
    parent_config = last_config
    
    missing = None
    if not cyclic:
        # Figure out if any parameters are missing
        missing = pool.config.getMissingParameters()
    
    data = { 'pool' : pool, 'parent_config' : parent_config, 'instances' : instances, 'config_params_missing' : missing, 'config_cyclic' : cyclic }
    
    return render(request, 'pools/view.html', data)

@login_required(login_url='/login/')
def viewPoolPrices(request, poolid):
    pool = get_object_or_404(InstancePool, pk=poolid)
    config = pool.config.flatten()
    prices = get_spot_prices(config.ec2_allowed_regions, config.aws_access_key_id, config.aws_secret_access_key, config.ec2_instance_type)

    zones = []
    latest_price_by_zone = {}
    
    for region in prices:
        for zone in prices[region]:
            zones.append(zone)
            latest_price_by_zone[zone] = prices[region][zone][-1]
        
    prices = []    
    for zone in sorted(zones):
        prices.append( (zone, latest_price_by_zone[zone]) )
            
    return render(request, 'pools/prices.html', { 'prices' : prices })

@login_required(login_url='/login/')
def disablePool(request, poolid):
    pool = get_object_or_404(InstancePool, pk=poolid)
    instances = Instance.objects.filter(pool=poolid)
    
    if not pool.isEnabled:
        return render(request, 'pools/error.html', { 'error_message' : 'That pool is already disabled.' })
            
    if request.method == 'POST':            
        pool.isEnabled = False
        pool.save()
        return redirect('ec2spotmanager:poolview', poolid=pool.pk)
    elif request.method == 'GET':
        return render(request, 'pools/disable.html', { 'pool' : pool, 'instanceCount' : len(instances) })
    else:
        raise SuspiciousOperation

@login_required(login_url='/login/')
def enablePool(request, poolid):
    pool = get_object_or_404(InstancePool, pk=poolid)
    
    # Safety check: Figure out if any parameters are missing
    # or if the configuration is cyclic, even though the link 
    # to this function should not be reachable in the UI at 
    # this point already.
    cyclic = pool.config.isCyclic()
    if cyclic:
        return render(request, 'pools/error.html', { 'error_message' : 'Pool configuration is cyclic.' })
    
    missing = pool.config.getMissingParameters()
    if missing:
        return render(request, 'pools/error.html', { 'error_message' : 'Pool is missing configuration parameters.' })
    
    size = pool.config.flatten().size
    
    if pool.isEnabled:
        return render(request, 'pools/error.html', { 'error_message' : 'That pool is already enabled.' })
    
    if request.method == 'POST':            
        pool.isEnabled = True
        pool.last_cycled = None
        pool.save()
        return redirect('ec2spotmanager:poolview', poolid=pool.pk)
    elif request.method == 'GET':
        return render(request, 'pools/enable.html', { 'pool' : pool, 'instanceCount' : size })
    else:
        raise SuspiciousOperation

@login_required(login_url='/login/')
def forceCyclePool(request, poolid):
    pool = get_object_or_404(InstancePool, pk=poolid)

    if not pool.isEnabled:
        return render(request, 'pools/error.html', { 'error_message' : 'Pool is disabled.' })
    
    size = pool.config.flatten().size
    
    if request.method == 'POST':
        pool.last_cycled = None
        pool.save()
        return redirect('ec2spotmanager:poolview', poolid=pool.pk)
    elif request.method == 'GET':
        return render(request, 'pools/cycle.html', { 'pool' : pool, 'instanceCount' : size })
    else:
        raise SuspiciousOperation

@login_required(login_url='/login/')
def createPool(request): 
    if request.method == 'POST':            
        pool = InstancePool()
        config = get_object_or_404(PoolConfiguration, pk=int(request.POST['config']))
        pool.config = config
        pool.save()
        return redirect('ec2spotmanager:poolview', poolid=pool.pk)
    elif request.method == 'GET':
        configurations = PoolConfiguration.objects.all()
        return render(request, 'pools/create.html', { 'configurations' : configurations })
    else:
        raise SuspiciousOperation

@login_required(login_url='/login/')
def viewConfigs(request):
    configs = PoolConfiguration.objects.all()
    roots = configs.filter(parent = None)
    
    def add_children(node):
        node.children = []
        children = configs.filter(parent = node)
        for child in children:
            node.children.append(child)
            add_children(child)
    
    for root in roots:
        add_children(root)      
    
    data = { 'roots' : roots }
    
    return render(request, 'config/index.html', data)

@login_required(login_url='/login/')
def viewConfig(request, configid):
    config = get_object_or_404(PoolConfiguration, pk=configid)
    
    data = { 'config' : config }
    
    return render(request, 'config/view.html', data)


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
    
    if request.POST['aws_access_key_id']:
        config.aws_access_key_id = request.POST['aws_access_key_id']
    else:
        config.aws_access_key_id = None
    
    if request.POST['aws_secret_access_key']:
        config.aws_secret_access_key = request.POST['aws_secret_access_key']
    else:
        config.aws_secret_access_key = None
        
    if request.POST['ec2_key_name']:
        config.ec2_key_name = request.POST['ec2_key_name']
    else:
        config.ec2_key_name = None
        
    if request.POST['ec2_instance_type']:
        config.ec2_instance_type = request.POST['ec2_instance_type']
    else:
        config.ec2_instance_type = None
        
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
        
    if request.POST['ec2_security_groups']:
        config.ec2_security_groups_list = [x.strip() for x in request.POST['ec2_security_groups'].split(',')]

    if request.POST['ec2_userdata_macros']:
        config.ec2_userdata_macros_dict = dict(y.split('=', 1) for y in [x.strip() for x in request.POST['ec2_userdata_macros'].split(',')]) 
        
    if request.POST['ec2_tags']:
        config.ec2_tags_dict = dict(y.split('=', 1) for y in [x.strip() for x in request.POST['ec2_tags'].split(',')]) 
    
    if request.POST['ec2_raw_config']:
        config.ec2_raw_config_dict = dict(y.split('=', 1) for y in [x.strip() for x in request.POST['ec2_raw_config'].split(',')])
    
    # Ensure we have a primary key before attempting to store files
    config.save()
    
    if request.POST['ec2_userdata']:
        if not config.ec2_userdata_file.name:
            config.ec2_userdata_file.save("default.sh", ContentFile(""))
        config.ec2_userdata = request.POST['ec2_userdata']
        config.storeTestAndSave()
    
    return redirect('ec2spotmanager:configview', configid=config.pk)

@login_required(login_url='/login/')
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
        
        data = { 'config' : config, 'configurations' : configurations, 'edit' : False, 'clone' : clone  }
        return render(request, 'config/edit.html', data)
    else:
        raise SuspiciousOperation

@login_required(login_url='/login/')
def editConfig(request, configid):
    config = get_object_or_404(PoolConfiguration, pk=configid)
    config.deserializeFields()
    
    if request.method == 'POST':
        return __handleConfigPOST(request, config)
    elif request.method == 'GET':
        configurations = PoolConfiguration.objects.all()
        data = { 'config' : config, 'configurations' : configurations, 'edit' : True }
        return render(request, 'config/edit.html', data)
    else:
        raise SuspiciousOperation

@login_required(login_url='/login/')
def deletePool(request, poolid):
    pool = get_object_or_404(InstancePool, pk=poolid)
    
    if pool.isEnabled:
        return render(request, 'pools/error.html', { 'error_message' : 'That pool is still enabled, you must disable it first.' })
    
    instances = Instance.objects.filter(pool=poolid)
    if instances:
        return render(request, 'pools/error.html', { 'error_message' : 'That pool still has instances associated with it. Please wait for their termination first.' })

    if request.method == 'POST':            
        pool.delete()
        return redirect('ec2spotmanager:pools')
    elif request.method == 'GET':
        return render(request, 'pools/delete.html', { 'pool' : pool })
    else:
        raise SuspiciousOperation

@login_required(login_url='/login/')
def deletePoolMsg(request, msgid):
    entry = get_object_or_404(PoolStatusEntry, pk=msgid)
    if request.method == 'POST':            
        entry.delete()
        return redirect('ec2spotmanager:pools')
    elif request.method == 'GET':
        return render(request, 'pools/messages/delete.html', { 'entry' : entry })
    else:
        raise SuspiciousOperation

@login_required(login_url='/login/')
def deleteConfig(request, configid):
    pass

class UptimeChartView(JSONView):
    def get_context_data(self, **kwargs):
        context = super(UptimeChartView, self).get_context_data(**kwargs)
        pool = InstancePool.objects.get(pk=int(kwargs['poolid']))
        pool.flat_config = pool.config.flatten()
        
        latest = now() - timedelta(hours=24)
        entries = PoolUptimeDetailedEntry.objects.filter(pool=pool, created__gt=latest).order_by('created')
        
        context.update({
                        'labels' : self.get_labels(pool, entries),
                        'datasets' : self.get_datasets(pool, entries),
                        'options' : self.get_options(pool, entries),
                        })
        return context

    def get_colors(self):
        return next_color()
    
    def get_data_colors(self, entries):
        colors = []
        red = (204,0,0)
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
            scaleSteps = pool.flat_config.size
        return { 
                'scaleOverride' : True,
                'scaleSteps' : scaleSteps,
                'scaleStepWidth' : 1,
                'scaleStartValue' : -1,
        }

    def get_datasets(self, pool, entries):
        datasets = []
        color_generator = self.get_colors()
        color = tuple(next(color_generator))
        
        data = [x.actual for x in entries]
        dataset = {
                   'fillColor': self.get_data_colors(entries),
                   #'highlightFill': "rgba(84,255,159,0.2)",
                   'strokeColor': "rgba(%d, %d, %d, 1)" % color,
                   'pointColor': "rgba(%d, %d, %d, 1)" % color,
                   'pointStrokeColor': "#fff",
                   'data': data
                   }
        
        datasets.append(dataset)
        return datasets

    def get_labels(self, pool, entries):
        return [x.created.strftime("%H:%M") for x in entries]