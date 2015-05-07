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
    
    # Figure out if our daemon is running
    daemonPidFile = os.path.join(settings.BASE_DIR, "daemon.pid")
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
                
    data = { 'isSearch' : isSearch, 'poollist' : entries, 'daemonRunning' : daemonRunning }
    
    return render(request, 'pools/index.html', data)


@login_required(login_url='/login/')
def viewPool(request, poolid):
    pool = get_object_or_404(InstancePool, pk=poolid)
    instances = Instance.objects.filter(pool=poolid)
    
    for instance in instances:
        instance.status_code_text = INSTANCE_STATE_CODE[instance.status_code]
    
    last_config = pool.config
    last_config.child = None
    parent_config = None
    
    while last_config.parent != None:
        last_config.parent.child = last_config
        last_config = last_config.parent
    
    if last_config != pool.config:
        parent_config = last_config
    
    data = { 'pool' : pool, 'parent_config' : parent_config, 'instances' : instances }
    
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
def createPool(request): 
    if request.method == 'POST':            
        pool = InstancePool()
        pool.config = int(request.POST['config'])
        pool.save()
        return redirect('ec2spotmanager:poolview', poolid=pool.pk)
    elif request.method == 'GET':
        configurations = PoolConfiguration.objects.all()
        return render(request, 'pools/create.html', { 'configurations' : configurations })
    else:
        raise SuspiciousOperation

@login_required(login_url='/login/')
def viewConfig(request, configid):
    config = get_object_or_404(PoolConfiguration, pk=configid)
    
    data = { 'config' : config }
    
    return render(request, 'pools/config.html', data)

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