from rest_framework import viewsets
from crashmanager.serializers import BucketSerializer, CrashEntrySerializer
from crashmanager.models import CrashEntry, Bucket, BugProvider, Bug
from django.template.context import RequestContext
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from FTB.Signatures.CrashInfo import CrashInfo
from FTB.ProgramConfiguration import ProgramConfiguration
from django.core.exceptions import SuspiciousOperation
from django.db.models import Q
from django.db.models.aggregates import Count
import json

def logout_view(request):
    logout(request)
    # Redirect to a success page.

@login_required(login_url='/login/')
def index(request):
    return redirect('crashmanager:crashes')

@login_required(login_url='/login/')
def allSignatures(request):
    entries = Bucket.objects.annotate(size=Count('crashentry'))
    context = RequestContext(request, { 'siglist' : entries })
    return render(request, 'signatures.html', context)

@login_required(login_url='/login/')
def allCrashes(request):
    entries = CrashEntry.objects.all()
    context = RequestContext(request, { 'crashlist' : entries })
    return render(request, 'crashes.html', context)

@login_required(login_url='/login/')
def signatures(request):
    entries = Bucket.objects.filter(bug=None).annotate(size=Count('crashentry'))
    context = RequestContext(request, { 'siglist' : entries })
    return render(request, 'signatures.html', context)

@login_required(login_url='/login/')
def crashes(request):
    filters = {}
    q = None
    isSearch = True
    
    entries = CrashEntry.objects.all();
    
    # These are all keys that are allowed for exact filtering
    exactFilterKeys = [
                       "bucket", 
                       "os__name",
                       "product__name",
                       "product__version",
                       "platform__name",
                       "testcase__quality",
                       ]
    
    for key in exactFilterKeys:
        if key in request.GET:
            filters[key] = request.GET[key]
    
    if "sig" in request.GET:
        filters["shortSignature__contains"] = request.GET["sig"]
        
    if "q" in request.GET:
        q = request.GET["q"]
        entries = entries.filter(
                                 Q(shortSignature__contains=q)
                                 | Q(rawStderr__contains=q)
                                 | Q(rawCrashData__contains=q)
                                 )

    # If we end up without any filters, the default is to show all issues that
    # have no bucket/signature associated yet, as they are considered untriaged
    if not filters and q == None:
        filters["bucket"] = None
        isSearch = False
    
    entries = entries.filter(**filters)
    context = RequestContext(request, {
                                       'q' : q,
                                       'request' : request,
                                       'isSearch' : isSearch, 
                                       'crashlist' : entries 
                                       })
    
    return render(request, 'crashes.html', context)

@login_required(login_url='/login/')
def autoAssignCrashEntries(request):
    entries = CrashEntry.objects.filter(bucket=None)
    buckets = Bucket.objects.all()
    
    for bucket in buckets:
        signature = bucket.getSignature()
        for entry in entries:
            if signature.matches(entry.getCrashInfo()):
                entry.bucket = bucket
                entry.save()
    
    return redirect('crashmanager:crashes')

@login_required(login_url='/login/')
def viewCrashEntry(request, crashid):
    entry = get_object_or_404(CrashEntry, pk=crashid)
    
    if entry.args:
        entry.argsList = json.loads(entry.args)

    if entry.env:
        envDict = json.loads(entry.env)
        entry.envList = ["%s=%s" % (s,envDict[s]) for s in envDict.keys()]
        
    if entry.testcase and not entry.testcase.isBinary:
        entry.testcase.test.open(mode='r')
        entry.testcase.content = entry.testcase.test.read()
        entry.testcase.test.close()
    
    context = RequestContext(request, { 'entry' : entry })
    return render(request, 'crash_view.html', context)

def __handleSignaturePost(request, bucket):
    # This method contains code shared between newSignature and editSignature
    # and handles the POST request processing after the bucket object has been
    # either fetched or created.
    try:
        signature = bucket.getSignature()
    except RuntimeError, e:
        context = RequestContext(request, { 'bucket' : bucket, 'error_message' : 'Signature is not valid: %s' % e })
        return render(request, 'signature_edit.html', context)
    
    # Only save if we hit "save" (not e.g. "preview")
    if 'submit_save' in request.POST:
        bucket.save()
    
    # If the reassign checkbox is checked, assign all unassigned issues that match
    # our signature to this bucket. Furthermore, remove all non-matching issues
    # from our bucket.
    #
    # Again, we only actually save if we hit "save". For previewing, we just count
    # how many issues would be assigned and removed.
    if "reassign" in request.POST:
        (inCount, outCount) = (0,0)
        
        signature = bucket.getSignature()
        entries = CrashEntry.objects.filter(Q(bucket=None) | Q(bucket=bucket))
        
        for entry in entries:
            match = signature.matches(entry.getCrashInfo())
            if match and entry.bucket == None:
                inCount += 1
                if 'submit_save' in request.POST:
                    entry.bucket = bucket
                    entry.save()
            elif not match and entry.bucket != None:
                outCount += 1
                if 'submit_save' in request.POST:
                    entry.bucket = None
                    entry.save()
    
    # Save bucket and redirect to viewing it       
    if 'submit_save' in request.POST:
        return redirect('crashmanager:sigview', sigid=bucket.pk)
    
    # Render the preview page
    context = RequestContext(request, { 'bucket' : bucket, 
                                       'error_message' : "This is a preview, don't forget to save!",
                                       'inCount' : inCount, 'outCount' : outCount
                                       })
    return render(request, 'signature_edit.html', context)

@login_required(login_url='/login/')
def newSignature(request):
    if request.method == 'POST':
        #TODO: FIXME: Update bug here as well
        bucket = Bucket(signature=request.POST['signature'], 
                            shortDescription=request.POST['shortDescription'])
        return __handleSignaturePost(request, bucket)
    elif request.method == 'GET':
        if 'crashid' in request.GET:
            crashEntry = get_object_or_404(CrashEntry, pk=request.GET['crashid'])
            
            configuration = ProgramConfiguration(crashEntry.product.name, 
                                                 crashEntry.platform.name, 
                                                 crashEntry.os.name, 
                                                 crashEntry.product.version)
            
            crashInfo = CrashInfo.fromRawCrashData(crashEntry.rawStdout, 
                                                   crashEntry.rawStderr, 
                                                   configuration, 
                                                   crashEntry.rawCrashData)
            
            proposedSignature = str(crashInfo.createCrashSignature())
            proposedShortDesc = crashInfo.createShortSignature()
            
            context = RequestContext(request, { 'new' : True, 'bucket' : { 
                                                            'pk' : None, 
                                                            'bug' : None,
                                                            'signature' : proposedSignature,
                                                            'shortDescription' : proposedShortDesc,
                                                            } })
        else:
            context = RequestContext(request, { 'new' : True })
    else:
        raise SuspiciousOperation
        
    return render(request, 'signature_edit.html', context)

@login_required(login_url='/login/')
def deleteSignature(request, sigid):
    bucket = get_object_or_404(Bucket, pk=sigid)
    if request.method == 'POST':    
        # Make sure we remove this bucket from all crash entries referring to it,
        # otherwise these would be deleted as well through cascading.
        CrashEntry.objects.filter(bucket=bucket).update(bucket=None)
        
        bucket.delete()
        return redirect('crashmanager:signatures')
    elif request.method == 'GET':
        context = RequestContext(request, { 'bucket' : bucket })
        return render(request, 'signature_del.html', context)
    else:
        raise SuspiciousOperation

@login_required(login_url='/login/')
def viewSignature(request, sigid):
    bucket = get_object_or_404(Bucket, pk=sigid)
    count = len(CrashEntry.objects.filter(bucket=bucket))
    context = RequestContext(request, { 'bucket' : bucket, 'crashcount' : count })
    return render(request, 'signature_view.html', context)

@login_required(login_url='/login/')
def editSignature(request, sigid):
    if request.method == 'POST':
        bucket = get_object_or_404(Bucket, pk=sigid)
        bucket.signature = request.POST['signature']
        bucket.shortDescription = request.POST['shortDescription']
        #TODO: FIXME: Update bug here as well
        return __handleSignaturePost(request, bucket)
    elif request.method == 'GET':
        if sigid != None:
            bucket = get_object_or_404(Bucket, pk=sigid)
            context = RequestContext(request, { 'bucket' : bucket })
        else:
            raise SuspiciousOperation
    else:
        raise SuspiciousOperation
        
    return render(request, 'signature_edit.html', context)

@login_required(login_url='/login/')
def createExternalBug(request, crashid):
    entry = get_object_or_404(CrashEntry, pk=crashid)
    if request.method == 'POST':
        provider = get_object_or_404(BugProvider, pk=request.POST['provider'])
        
        # Let the provider handle the POST request, which will file the bug
        # and return us the external bug ID
        extBugId = provider.getInstance().handlePOSTCreate(request)
        
        # Now create a bug in our database with that ID and assign it to the bucket
        extBug = Bug(externalId = extBugId, externalType = provider)
        entry.bucket.bug = extBug
        entry.bucket.save()
        
        return redirect('crashmanager:sigview', sigid=entry.bucket.pk)
    elif request.method == 'GET':
        if 'provider' in request.GET:
            provider = get_object_or_404(BugProvider, pk=request.GET['provider'])
        else:
            provider = get_object_or_404(BugProvider, pk=1)
        
        return provider.getInstance().renderContextCreate(request, entry)
    else:
        raise SuspiciousOperation

class CrashEntryViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows adding/viewing CrashEntries
    """
    queryset = CrashEntry.objects.all()
    serializer_class = CrashEntrySerializer


class BucketViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows reading of signatures
    """
    queryset = Bucket.objects.all()
    serializer_class = BucketSerializer