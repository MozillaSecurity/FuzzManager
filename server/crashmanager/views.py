from collections import OrderedDict
from datetime import datetime, timedelta
from django.core.exceptions import FieldError, SuspiciousOperation, PermissionDenied
from django.db.models import F, Q
from django.db.models.aggregates import Count, Min
from django.http import Http404, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.generic import TemplateView
from django.views.generic.list import ListView
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from notifications.models import Notification
import json
import os
from rest_framework import mixins, status, viewsets
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from rest_framework.decorators import action
from rest_framework.exceptions import MethodNotAllowed, ValidationError
from rest_framework.filters import BaseFilterBackend, OrderingFilter
from rest_framework.response import Response
from rest_framework.views import APIView
import six

from wsgiref.util import FileWrapper

from FTB.ProgramConfiguration import ProgramConfiguration
from FTB.Signatures.CrashInfo import CrashInfo
from .forms import BugzillaTemplateBugForm, BugzillaTemplateCommentForm, UserSettingsForm
from .models import BugzillaTemplate, BugzillaTemplateMode, CrashEntry, Bucket, BucketHit, \
    BucketWatch, BugProvider, Bug, Tool, User
from .serializers import BugzillaTemplateSerializer, InvalidArgumentException, \
    BucketSerializer, BucketVueSerializer, CrashEntrySerializer, CrashEntryVueSerializer, \
    BugProviderSerializer, NotificationSerializer
from server.auth import CheckAppPermission

from django.conf import settings as django_settings


class JSONDateEncoder(json.JSONEncoder):

    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat().replace("+00:00", "Z")
        return super().default(obj)


def check_authorized_for_crash_entry(request, entry):
    user = User.get_or_create_restricted(request.user)[0]
    if user.restricted:
        defaultToolsFilter = user.defaultToolsFilter.all()
        if not defaultToolsFilter or entry.tool not in defaultToolsFilter:
            raise PermissionDenied({"message": "You don't have permission to access this crash entry."})

    return


def check_authorized_for_signature(request, signature):
    user = User.get_or_create_restricted(request.user)[0]
    if user.restricted:
        defaultToolsFilter = user.defaultToolsFilter.all()
        if not defaultToolsFilter:
            raise PermissionDenied({"message": "You don't have permission to access this signature."})

        entries = CrashEntry.objects.filter(bucket=signature)
        entries = CrashEntry.deferRawFields(entries)
        entries = entries.filter(tool__in=defaultToolsFilter)
        if not entries:
            raise PermissionDenied({"message": "You don't have permission to access this signature."})

    return


def deny_restricted_users(request):
    user = User.get_or_create_restricted(request.user)[0]
    if user.restricted:
        raise PermissionDenied({"message": "Restricted users cannot use this feature."})


def filter_crash_entries_by_toolfilter(request, entries, restricted_only=False):
    user = User.get_or_create_restricted(request.user)[0]

    if restricted_only and not user.restricted:
        return entries

    defaultToolsFilter = user.defaultToolsFilter.all()
    if defaultToolsFilter:
        return entries.filter(tool__in=defaultToolsFilter)
    elif user.restricted:
        return CrashEntry.objects.none()

    return entries


def filter_signatures_by_toolfilter(request, signatures, restricted_only=False, legacy_filters=True):
    user = User.get_or_create_restricted(request.user)[0]

    if restricted_only and not user.restricted:
        return signatures

    # allow legacy filters for web-ui based views
    # these don't work with the rest api (use `ignore_toolfilter` or `query` instead)
    if not user.restricted and legacy_filters:
        # If the user is unrestricted and all=1 is set, do not apply any filters
        if "all" in request.GET and request.GET["all"]:
            return signatures

        # Unrestricted users can filter the signature view for a single tool
        if "tool" in request.GET:
            tool_name = request.GET["tool"]
            tool = get_object_or_404(Tool, name=tool_name)
            return signatures.filter(crashentry__tool=tool)

    defaultToolsFilter = user.defaultToolsFilter.all()
    if defaultToolsFilter:
        return signatures.filter(crashentry__tool__in=set(defaultToolsFilter))
    elif user.restricted:
        return Bucket.objects.none()

    return signatures


def filter_bucket_hits_by_toolfilter(request, hits, restricted_only=False):
    user = User.get_or_create_restricted(request.user)[0]

    if restricted_only and not user.restricted:
        return hits

    defaultToolsFilter = user.defaultToolsFilter.all()
    if defaultToolsFilter:
        return hits.filter(tool__in=defaultToolsFilter)
    elif user.restricted:
        return BucketHit.objects.none()

    return hits


def renderError(request, err):
    return render(request, 'error.html', {'error_message': err})


def stats(request):
    lastHourDelta = timezone.now() - timedelta(hours=1)
    print(lastHourDelta)
    entries = CrashEntry.objects.filter(created__gt=lastHourDelta).select_related('bucket')
    entries = CrashEntry.deferRawFields(entries)
    entries = filter_crash_entries_by_toolfilter(request, entries, restricted_only=True)

    bucketFrequencyMap = {}
    for entry in entries:
        if entry.bucket is not None:
            if entry.bucket.pk in bucketFrequencyMap:
                bucketFrequencyMap[entry.bucket.pk] += 1
            else:
                bucketFrequencyMap[entry.bucket.pk] = 1

    frequentBuckets = []

    if bucketFrequencyMap:
        bucketFrequencyMap = sorted(bucketFrequencyMap.items(), key=lambda t: t[1], reverse=True)[:10]
        for pk, freq in bucketFrequencyMap:
            obj = Bucket.objects.get(pk=pk)
            obj.rph = freq
            frequentBuckets.append(obj)

    providers = BugProviderSerializer(BugProvider.objects.all(), many=True).data

    return render(request, 'stats.html', {
        'total_reports_per_hour': len(entries),
        'frequentBuckets': frequentBuckets,
        'providers': json.dumps(providers),
    })


def settings(request):
    return render(request, 'settings.html')


def watchedSignatures(request):
    # for this user, list watches
    # buckets   sig       new crashes   remove
    # ========================================
    # 1         crash       10          tr
    # 2         assert      0           tr
    # 3         blah        0           tr
    user = User.get_or_create_restricted(request.user)[0]

    filters = {
        'user': user,
        'crashentry__gt': F('bucketwatch__lastCrash'),
    }
    # the join of Bucket+CrashEntry is a big one, and each filter() call on a related field adds a join
    # therefore this needs to be a single filter() call, otherwise we get duplicate crashentries in the result
    # this is why tool filtering is done manually here and not using filter_signatures_by_toolfilter()
    defaultToolsFilter = user.defaultToolsFilter.all()
    if defaultToolsFilter:
        filters['crashentry__tool__in'] = defaultToolsFilter
    buckets = Bucket.objects.filter(**filters)
    buckets = buckets.annotate(newCrashes=Count('crashentry'))
    buckets = buckets.extra(select={'lastCrash': 'crashmanager_bucketwatch.lastCrash'})
    # what's left is only watched buckets with new crashes
    # need to include other watched buckets too .. which means evaluating the buckets query now
    newBuckets = list(buckets)
    # get all buckets watched by this user
    # this is the result, but we will replace any buckets also found in newBuckets
    bucketsAll = Bucket.objects.filter(user=user).order_by('-id')
    bucketsAll = bucketsAll.extra(select={'lastCrash': 'crashmanager_bucketwatch.lastCrash'})
    buckets = list(bucketsAll)
    for idx, bucket in enumerate(buckets):
        for newIdx, newBucket in enumerate(newBuckets):
            if newBucket == bucket:
                # replace with this one
                buckets[idx] = newBucket
                newBuckets.pop(newIdx)
                break
        else:
            bucket.newCrashes = 0
    return render(request, 'signatures/watch.html', {'siglist': buckets})


def deleteBucketWatch(request, sigid):
    user = User.get_or_create_restricted(request.user)[0]

    if request.method == 'POST':
        entry = get_object_or_404(BucketWatch, user=user, bucket=sigid)
        entry.delete()
        return redirect('crashmanager:sigwatch')
    elif request.method == 'GET':
        entry = get_object_or_404(Bucket, user=user, pk=sigid)
        return render(request, 'signatures/watch_remove.html', {'entry': entry})
    else:
        raise SuspiciousOperation()


def newBucketWatch(request):
    if request.method == 'POST':
        user = User.get_or_create_restricted(request.user)[0]
        bucket = get_object_or_404(Bucket, pk=int(request.POST['bucket']))
        for watch in BucketWatch.objects.filter(user=user, bucket=bucket):
            watch.lastCrash = int(request.POST['crash'])
            watch.save()
            break
        else:
            BucketWatch.objects.create(user=user,
                                       bucket=bucket,
                                       lastCrash=int(request.POST['crash']))
        return redirect('crashmanager:sigwatch')
    raise SuspiciousOperation()


def bucketWatchCrashes(request, sigid):
    user = User.get_or_create_restricted(request.user)[0]
    bucket = get_object_or_404(Bucket, pk=sigid)
    watch = get_object_or_404(BucketWatch, user=user, bucket=bucket)
    return render(request, 'crashes/index.html', {'restricted': user.restricted, 'watchId': watch.id})


def signatures(request):
    providers = BugProviderSerializer(BugProvider.objects.all(), many=True).data
    return render(
        request,
        'signatures/index.html',
        {
            'providers': json.dumps(providers),
            'activity_range': getattr(django_settings, "CLEANUP_CRASHES_AFTER_DAYS", 14),
        },
    )


def index(request):
    return redirect('crashmanager:crashes')


def crashes(request):
    user = User.get_or_create_restricted(request.user)[0]
    return render(request, 'crashes/index.html', {'restricted': user.restricted})


def viewCrashEntry(request, crashid):
    entry = get_object_or_404(CrashEntry, pk=crashid)
    check_authorized_for_crash_entry(request, entry)
    entry.deserializeFields()

    if entry.testcase and not entry.testcase.isBinary:
        entry.testcase.loadTest()

    providers = BugProviderSerializer(BugProvider.objects.all(), many=True).data

    return render(request, 'crashes/view.html', {'entry': entry, 'providers': json.dumps(providers)})


def editCrashEntry(request, crashid):
    entry = get_object_or_404(CrashEntry, pk=crashid)
    check_authorized_for_crash_entry(request, entry)
    entry.deserializeFields()

    if entry.testcase:
        entry.testcase.loadTest()

    if request.method == 'POST':
        entry.rawStdout = request.POST['rawStdout']
        entry.rawStderr = request.POST['rawStderr']
        entry.rawStderr = request.POST['rawStderr']
        entry.rawCrashData = request.POST['rawCrashData']

        entry.envList = request.POST['env'].splitlines()
        entry.argsList = request.POST['args'].splitlines()
        entry.metadataList = request.POST['metadata'].splitlines()

        # Regenerate crash information and fields depending on it
        entry.reparseCrashInfo()

        if entry.testcase:
            if entry.testcase.isBinary:
                if request.POST['testcase'] != "(binary)":
                    entry.testcase.content = request.POST['testcase']
                    entry.testcase.isBinary = False
                    # TODO: The file extension stored on the server remains and is likely to be wrong
                    entry.testcase.storeTestAndSave()
            else:
                if request.POST['testcase'] != entry.testcase.content:
                    entry.testcase.content = request.POST['testcase']
                    entry.testcase.storeTestAndSave()

        return redirect('crashmanager:crashview', crashid=entry.pk)
    else:
        return render(request, 'crashes/edit.html', {'entry': entry})


def deleteCrashEntry(request, crashid):
    entry = get_object_or_404(CrashEntry, pk=crashid)
    check_authorized_for_crash_entry(request, entry)

    if request.method == 'POST':
        entry.delete()
        return redirect('crashmanager:crashes')
    elif request.method == 'GET':
        return render(request, 'crashes/remove.html', {'entry': entry})
    else:
        raise SuspiciousOperation


def newSignature(request):
    if request.method != 'GET':
        raise SuspiciousOperation

    data = {}
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

        maxStackFrames = 8
        forceCrashInstruction = False
        forceCrashAddress = True
        errorMsg = None

        if 'stackframes' in request.GET:
            maxStackFrames = int(request.GET['stackframes'])
        elif set(crashInfo.backtrace) & {
                "std::panicking::rust_panic",
                "std::panicking::rust_panic_with_hook",
        }:
            # rust panic adds 5-6 frames of noise at the top of the stack
            maxStackFrames += 6

        if 'forcecrashaddress' in request.GET:
            forceCrashAddress = bool(int(request.GET['forcecrashaddress']))

        if 'forcecrashinstruction' in request.GET:
            forceCrashInstruction = bool(int(request.GET['forcecrashinstruction']))

        # First try to create the signature with the crash address included.
        # However, if that fails, try without forcing the crash signature.
        proposedSignature = crashInfo.createCrashSignature(
            forceCrashAddress=forceCrashAddress,
            forceCrashInstruction=forceCrashInstruction,
            maxFrames=maxStackFrames
        )
        if proposedSignature is None:
            errorMsg = crashInfo.failureReason
            proposedSignature = crashInfo.createCrashSignature(maxFrames=maxStackFrames)

        proposedSignature = str(proposedSignature)
        proposedShortDesc = crashInfo.createShortSignature()

        data = {
            'proposedSig': json.loads(proposedSignature),
            'proposedDesc': proposedShortDesc,
            'warningMessage': errorMsg
        }

    return render(request, 'signatures/edit.html', data)


def deleteSignature(request, sigid):
    bucket = Bucket.objects.filter(pk=sigid).annotate(size=Count('crashentry'))
    if not bucket:
        raise Http404
    bucket = bucket[0]

    check_authorized_for_signature(request, bucket)

    if request.method == 'POST':
        if "delentries" not in request.POST:
            # Make sure we remove this bucket from all crash entries referring to it,
            # otherwise these would be deleted as well through cascading.
            CrashEntry.objects.filter(bucket=bucket).update(bucket=None, triagedOnce=False)

        bucket.delete()
        return redirect('crashmanager:signatures')
    elif request.method == 'GET':
        return render(request, 'signatures/remove.html', {'bucket': bucket})
    else:
        raise SuspiciousOperation


def viewSignature(request, sigid):
    response = BucketVueViewSet.as_view({'get': 'retrieve'})(request, pk=sigid)
    if response.status_code == 404:
        raise Http404
    elif response.status_code != 200:
        return response
    bucket = response.data
    if bucket['best_entry'] is not None:
        best_entry_size = get_object_or_404(CrashEntry, pk=bucket['best_entry']).testcase.size
    else:
        best_entry_size = None
    providers = BugProviderSerializer(BugProvider.objects.all(), many=True).data

    return render(request, 'signatures/view.html', {
        'activity_range': getattr(django_settings, "CLEANUP_CRASHES_AFTER_DAYS", 14),
        'bucket': json.dumps(bucket, cls=JSONDateEncoder),
        'bucket_id': bucket['id'],
        'best_entry': bucket['best_entry'],
        'best_entry_size': json.dumps(best_entry_size),
        'providers': json.dumps(providers),
    })


def editSignature(request, sigid):
    if request.method != 'GET' or sigid is None:
        raise SuspiciousOperation

    bucket = get_object_or_404(Bucket, pk=sigid)
    check_authorized_for_signature(request, bucket)

    proposedSignature = None
    if 'fit' in request.GET:
        entry = get_object_or_404(CrashEntry, pk=request.GET['fit'])
        proposedSignature = bucket.getSignature().fit(entry.getCrashInfo())

    return render(request, 'signatures/edit.html', {'bucketId': bucket.pk, 'proposedSig': proposedSignature})


def trySignature(request, sigid, crashid):
    bucket = get_object_or_404(Bucket, pk=sigid)
    check_authorized_for_signature(request, bucket)

    entry = get_object_or_404(CrashEntry, pk=crashid)
    check_authorized_for_crash_entry(request, entry)

    signature = bucket.getSignature()
    entry.crashinfo = entry.getCrashInfo(attachTestcase=signature.matchRequiresTest())

    # symptoms = signature.getSymptomsDiff(entry.crashinfo)
    diff = signature.getSignatureUnifiedDiffTuples(entry.crashinfo)

    return render(request, 'signatures/try.html', {'bucket': bucket, 'entry': entry, 'diff': diff})


def optimizeSignature(request, sigid):
    bucket = get_object_or_404(Bucket, pk=sigid)
    check_authorized_for_signature(request, bucket)

    # Get all unbucketed entries for that user, respecting the tools filter though
    entries = CrashEntry.objects.filter(bucket=None).order_by('-id').select_related("platform", "product", "os", "tool")
    entries = filter_crash_entries_by_toolfilter(request, entries, restricted_only=True)

    (optimizedSignature, matchingEntries) = bucket.optimizeSignature(entries)
    diff = None
    if optimizedSignature:
        diff = bucket.getSignature().getSignatureUnifiedDiffTuples(matchingEntries[0].crashinfo)

    return render(request, 'signatures/optimize.html', {'bucket': bucket, 'optimizedSignature': optimizedSignature,
                                                        'diff': diff, 'matchingEntries': matchingEntries})


def optimizeSignaturePrecomputed(request, sigid):
    bucket = get_object_or_404(Bucket, pk=sigid)
    check_authorized_for_signature(request, bucket)

    if not bucket.optimizedSignature:
        raise Http404

    # Get all unbucketed entries for that user, respecting the tools filter though
    entries = CrashEntry.objects.filter(bucket=None).order_by('-id').select_related("platform", "product", "os", "tool")
    entries = filter_crash_entries_by_toolfilter(request, entries, restricted_only=True)

    optimizedSignature = bucket.getOptimizedSignature()
    requiredOutputs = optimizedSignature.getRequiredOutputSources()
    entries = CrashEntry.deferRawFields(entries, requiredOutputs)

    # Recompute matching entries based on current state
    matchingEntries = []
    for entry in entries:
        entry.crashinfo = entry.getCrashInfo(attachTestcase=optimizedSignature.matchRequiresTest(),
                                             requiredOutputSources=requiredOutputs)
        if optimizedSignature.matches(entry.crashinfo):
            matchingEntries.append(entry)

    diff = None
    if matchingEntries:
        # TODO: Handle this more gracefully
        diff = bucket.getSignature().getSignatureUnifiedDiffTuples(matchingEntries[0].crashinfo)

    return render(request, 'signatures/optimize.html', {'bucket': bucket, 'optimizedSignature': optimizedSignature,
                                                        'diff': diff, 'matchingEntries': matchingEntries})


def findSignatures(request, crashid):
    entry = get_object_or_404(CrashEntry, pk=crashid)
    check_authorized_for_crash_entry(request, entry)

    entry.crashinfo = entry.getCrashInfo(attachTestcase=True)

    buckets = Bucket.objects.all()
    buckets = filter_signatures_by_toolfilter(request, buckets, restricted_only=True)
    similarBuckets = []
    matchingBucket = None

    # Avoid hitting the database multiple times when looking for the first
    # entry of a bucket. Keeping these in memory is less expensive.
    firstEntryPerBucketCache = {}

    for bucket in buckets:
        signature = bucket.getSignature()
        distance = signature.getDistance(entry.crashinfo)

        # We found a matching bucket, no need to display/calculate similar buckets
        if distance == 0:
            matchingBucket = bucket
            break

        # TODO: This could be made configurable through a GET parameter
        if distance <= 4:
            proposedCrashSignature = signature.fit(entry.crashinfo)
            if proposedCrashSignature:
                # We now try to determine how this signature will behave in other buckets
                # If the signature matches lots of other buckets as well, it is likely too
                # broad and we should not consider it (or later rate it worse than others).
                matchesInOtherBuckets = 0
                matchesInOtherBucketsLimitExceeded = False
                nonMatchesInOtherBuckets = 0
                otherMatchingBucketIds = []
                for otherBucket in buckets:
                    if otherBucket.pk == bucket.pk:
                        continue

                    if otherBucket.pk not in firstEntryPerBucketCache:
                        c = CrashEntry.objects.filter(bucket=otherBucket).first()
                        firstEntryPerBucketCache[otherBucket.pk] = c
                        if c:
                            # Omit testcase for performance reasons for now
                            firstEntryPerBucketCache[otherBucket.pk] = c.getCrashInfo(attachTestcase=False)

                    firstEntryCrashInfo = firstEntryPerBucketCache[otherBucket.pk]
                    if firstEntryCrashInfo:
                        # Omit testcase for performance reasons for now
                        if proposedCrashSignature.matches(firstEntryCrashInfo):
                            matchesInOtherBuckets += 1
                            otherMatchingBucketIds.append(otherBucket.pk)

                            # We already match too many foreign buckets. Abort our search here
                            # to speed up the response time.
                            if matchesInOtherBuckets > 5:
                                matchesInOtherBucketsLimitExceeded = True
                                break
                        else:
                            nonMatchesInOtherBuckets += 1

                bucket.offCount = distance

                if matchesInOtherBuckets + nonMatchesInOtherBuckets > 0:
                    bucket.foreignMatchPercentage = round((float(matchesInOtherBuckets) / (
                        matchesInOtherBuckets + nonMatchesInOtherBuckets)) * 100, 2)
                else:
                    bucket.foreignMatchPercentage = 0

                bucket.foreignMatchCount = matchesInOtherBuckets
                bucket.foreignMatchLimitExceeded = matchesInOtherBucketsLimitExceeded

                if matchesInOtherBuckets == 0:
                    bucket.foreignColor = "green"
                elif matchesInOtherBuckets < 3:
                    bucket.foreignColor = "yellow"
                else:
                    bucket.foreignColor = "red"

                # Only include the bucket in our results if the number of matches in other buckets is below
                # out limit. Otherwise, it will just distract the user.
                if matchesInOtherBuckets <= 5:
                    bucket.linkToOthers = ",".join([str(x) for x in otherMatchingBucketIds])
                    similarBuckets.append(bucket)

    if matchingBucket:
        entry.bucket = matchingBucket
        entry.save(update_fields=['bucket'])
        return render(request, 'signatures/find.html', {'bucket': matchingBucket, 'crashentry': entry})
    else:
        similarBuckets.sort(key=lambda x: (x.foreignMatchCount, x.offCount))
        return render(request, 'signatures/find.html', {'buckets': similarBuckets, 'crashentry': entry})


def createExternalBug(request, crashid):
    entry = get_object_or_404(CrashEntry, pk=crashid)
    check_authorized_for_crash_entry(request, entry)

    if not entry.bucket:
        return renderError(request, ("Cannot create an external bug for an issue that is not associated "
                                     "to a bucket/signature"))

    if request.method == 'GET':
        if 'provider' in request.GET:
            provider = get_object_or_404(BugProvider, pk=request.GET['provider'])
        else:
            user = User.get_or_create_restricted(request.user)[0]
            provider = get_object_or_404(BugProvider, pk=user.defaultProviderId)

        template = provider.getInstance().getTemplateForUser(request, entry)
        data = {
            'provider': provider.pk,
            'hostname': provider.hostname,
            'template': template['pk'] if template else -1,
            'entry': entry,
        }
        return render(request, 'bugzilla/create_external_bug.html', data)
    else:
        raise SuspiciousOperation


def createExternalBugComment(request, crashid):
    entry = get_object_or_404(CrashEntry, pk=crashid)
    check_authorized_for_crash_entry(request, entry)

    if request.method == 'GET':
        if 'provider' in request.GET:
            provider = get_object_or_404(BugProvider, pk=request.GET['provider'])
        else:
            user = User.get_or_create_restricted(request.user)[0]
            provider = get_object_or_404(BugProvider, pk=user.defaultProviderId)

        template = provider.getInstance().getTemplateForUser(request, entry)
        data = {
            'provider': provider.pk,
            'hostname': provider.hostname,
            'template': template['pk'] if template else -1,
            'entry': entry,
        }
        return render(request, 'bugzilla/create_external_comment.html', data)
    else:
        raise SuspiciousOperation


def viewBugProviders(request):
    providers = BugProvider.objects.annotate(size=Count('bug'))
    return render(request, 'providers/index.html', {'providers': providers})


def deleteBugProvider(request, providerId):
    deny_restricted_users(request)

    provider = get_object_or_404(BugProvider, pk=providerId)
    if request.method == 'POST':
        # Deassociate all bugs
        bugs = Bug.objects.filter(externalType=provider.pk)
        buckets = Bucket.objects.filter(bug__in=bugs)
        for bucket in buckets:
            bucket.bug = None
            bucket.save(update_fields=['bug'])

        provider.delete()
        return redirect('crashmanager:bugproviders')
    elif request.method == 'GET':
        return render(request, 'providers/remove.html', {'provider': provider})
    else:
        raise SuspiciousOperation


def viewBugProvider(request, providerId):
    provider = BugProvider.objects.filter(pk=providerId).annotate(size=Count('bug'))

    if not provider:
        raise Http404

    provider = provider[0]

    return render(request, 'providers/view.html', {'provider': provider})


def editBugProvider(request, providerId):
    deny_restricted_users(request)

    provider = get_object_or_404(BugProvider, pk=providerId)
    if request.method == 'POST':
        provider.classname = request.POST['classname']
        provider.hostname = request.POST['hostname']
        provider.urlTemplate = request.POST['urlTemplate']

        try:
            provider.getInstance()
        except Exception as e:
            return render(request, 'providers/edit.html', {'provider': provider, 'error_message': e})

        provider.save()
        return redirect('crashmanager:bugproviders')
    elif request.method == 'GET':
        return render(request, 'providers/edit.html', {'provider': provider})
    else:
        raise SuspiciousOperation


def createBugProvider(request):
    deny_restricted_users(request)

    if request.method == 'POST':
        provider = BugProvider(classname=request.POST['classname'], hostname=request.POST['hostname'],
                               urlTemplate=request.POST['urlTemplate'])

        try:
            provider.getInstance()
        except Exception as e:
            return render(request, 'providers/edit.html', {'provider': provider, 'error_message': e})

        provider.save()
        return redirect('crashmanager:bugproviders')
    elif request.method == 'GET':
        return render(request, 'providers/edit.html', {})
    else:
        raise SuspiciousOperation


def duplicateBugzillaTemplate(request, templateId):
    clone = get_object_or_404(BugzillaTemplate, pk=templateId)
    clone.pk = None  # to autogen a new pk on save()
    clone.name = "Clone of " + clone.name
    clone.save()
    return redirect('crashmanager:templates')


class JsonQueryFilterBackend(BaseFilterBackend):
    """
    Accepts filtering with a query parameter which builds a Django query from JSON (see json_to_query)
    """
    def filter_queryset(self, request, queryset, view):
        """
        Return a filtered queryset.
        """
        querystr = request.query_params.get('query', None)
        if querystr is not None:
            try:
                _, queryobj = json_to_query(querystr)
            except (RuntimeError, TypeError) as e:
                raise InvalidArgumentException("error in query: %s" % e)
            try:
                queryset = queryset.filter(queryobj)
            except FieldError as exc:
                raise InvalidArgumentException("error in query: %s" % exc)
        return queryset


class ToolFilterCrashesBackend(BaseFilterBackend):
    """
    Filters the queryset by the user's toolfilter unless '?ignore_toolfilter=1' is given.
    Only unrestricted users can use ignore_toolfilter.
    """
    def filter_queryset(self, request, queryset, view):
        """Return a filtered queryset"""
        ignore_toolfilter = request.query_params.get('ignore_toolfilter', '0')
        try:
            ignore_toolfilter = int(ignore_toolfilter)
            assert ignore_toolfilter in {0, 1}
        except (AssertionError, ValueError):
            raise InvalidArgumentException({'ignore_toolfilter': ['Expecting 0 or 1.']})
        view.ignore_toolfilter = bool(ignore_toolfilter)
        return filter_crash_entries_by_toolfilter(
            request, queryset,
            restricted_only=bool(view.ignore_toolfilter) or view.action != "list")


class WatchFilterCrashesBackend(BaseFilterBackend):
    """Filters the queryset to retrieve watched entries if '?watch=<int>'"""
    def filter_queryset(self, request, queryset, view):
        watch_id = request.query_params.get('watch', 'false').lower()
        if watch_id == 'false':
            return queryset
        watch = BucketWatch.objects.get(id=watch_id)
        return queryset.filter(bucket=watch.bucket, id__gt=watch.lastCrash)


class ToolFilterSignaturesBackend(BaseFilterBackend):
    """
    Filters the queryset by the user's toolfilter unless '?ignore_toolfilter=1' is given.
    Only unrestricted users can use ignore_toolfilter.
    """
    def filter_queryset(self, request, queryset, view):
        """Return a filtered queryset"""
        ignore_toolfilter = request.query_params.get('ignore_toolfilter', '0')
        try:
            ignore_toolfilter = int(ignore_toolfilter)
            assert ignore_toolfilter in {0, 1}
        except (AssertionError, ValueError):
            raise InvalidArgumentException({'ignore_toolfilter': ['Expecting 0 or 1.']})
        view.ignore_toolfilter = bool(ignore_toolfilter)
        return filter_signatures_by_toolfilter(
            request, queryset, legacy_filters=False,
            restricted_only=bool(view.ignore_toolfilter) or view.action != "list")


class BucketAnnotateFilterBackend(BaseFilterBackend):
    """Annotates bucket queryset with size and best_quality"""
    def filter_queryset(self, request, queryset, view):
        return queryset.annotate(size=Count('crashentry'), quality=Min('crashentry__testcase__quality'))


class DeferRawFilterBackend(BaseFilterBackend):
    """Optionally defer raw fields"""
    def filter_queryset(self, request, queryset, view):
        include_raw = request.query_params.get('include_raw', '1')
        try:
            include_raw = int(include_raw)
            assert include_raw in {0, 1}
        except (AssertionError, ValueError):
            raise InvalidArgumentException({'include_raw': ['Expecting 0 or 1.']})

        if not include_raw:
            queryset = queryset.defer('rawStdout', 'rawStderr', 'rawCrashData')

        view.include_raw = bool(include_raw)
        return queryset


class CrashEntryViewSet(mixins.CreateModelMixin,
                        mixins.ListModelMixin,
                        mixins.RetrieveModelMixin,
                        viewsets.GenericViewSet):
    """API endpoint that allows adding/viewing CrashEntries"""
    authentication_classes = (TokenAuthentication, SessionAuthentication)
    queryset = CrashEntry.objects.all().select_related('product', 'platform', 'os', 'client', 'tool', 'testcase')
    serializer_class = CrashEntrySerializer
    filter_backends = [
        WatchFilterCrashesBackend,
        ToolFilterCrashesBackend,
        JsonQueryFilterBackend,
        OrderingFilter,
        DeferRawFilterBackend
    ]

    def get_serializer(self, *args, **kwds):
        kwds["include_raw"] = getattr(self, "include_raw", True)
        vue = self.request.query_params.get('vue', 'false').lower() not in ('false', '0')
        if vue:
            return CrashEntryVueSerializer(*args, **kwds)
        else:
            return super(CrashEntryViewSet, self).get_serializer(*args, **kwds)

    def partial_update(self, request, pk=None):
        """Update individual crash fields."""
        user = User.get_or_create_restricted(request.user)[0]
        if user.restricted:
            raise MethodNotAllowed(request.method)

        allowed_fields = {"testcase_quality"}
        try:
            obj = CrashEntry.objects.get(pk=pk)
        except CrashEntry.DoesNotExist:
            raise Http404
        given_fields = set(request.data.keys())
        disallowed_fields = given_fields - allowed_fields
        if disallowed_fields:
            if len(disallowed_fields) == 1:
                error_str = "field %r" % disallowed_fields.pop()
            else:
                error_str = "fields %r" % list(disallowed_fields)
            raise InvalidArgumentException("%s cannot be updated" % error_str)
        if "testcase_quality" in request.data:
            if obj.testcase is None:
                raise InvalidArgumentException("crash has no testcase")
            try:
                testcase_quality = int(request.data["testcase_quality"])
            except ValueError:
                raise InvalidArgumentException("invalid testcase_quality")
            # NB: if other fields are added, all validation should occur before any DB writes.
            obj.testcase.quality = testcase_quality
            obj.testcase.save()
        return Response(CrashEntrySerializer(obj).data)


class BucketViewSet(mixins.CreateModelMixin,
                    mixins.ListModelMixin,
                    mixins.UpdateModelMixin,
                    viewsets.GenericViewSet):
    """API endpoint that allows viewing Buckets"""
    authentication_classes = (TokenAuthentication, SessionAuthentication)
    queryset = Bucket.objects.all().select_related('bug', 'bug__externalType')
    serializer_class = BucketSerializer
    filter_backends = [ToolFilterSignaturesBackend, JsonQueryFilterBackend, BucketAnnotateFilterBackend, OrderingFilter]
    ordering_fields = ['id', 'shortDescription', 'size', 'quality', 'optimizedSignature', 'bug__externalId']
    pagination_class = None

    def get_serializer(self, *args, **kwds):
        self.vue = self.request.query_params.get('vue', 'false').lower() not in ('false', '0')
        if self.vue:
            return BucketVueSerializer(*args, **kwds)
        else:
            return super(BucketViewSet, self).get_serializer(*args, **kwds)

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)

        if self.vue and response.status_code == 200:
            # no need to sanity check, this was already checked in ToolFilterSignaturesBackend filter
            ignore_toolfilter = int(request.query_params.get('ignore_toolfilter', '0'))
            hits = filter_bucket_hits_by_toolfilter(
                request,
                BucketHit.objects.all(),
                restricted_only=bool(ignore_toolfilter),
            ).filter(
                begin__gte=timezone.now() - timedelta(days=getattr(django_settings, "CLEANUP_CRASHES_AFTER_DAYS", 14)),
                bucket_id__in=[bucket["id"] for bucket in response.data],
            ).order_by("begin")

            bucket_hits = {}
            for bucket, begin, count in hits.values_list("bucket_id", "begin", "count"):
                bucket_hits.setdefault(bucket, {})
                bucket_hits[bucket].setdefault(begin, 0)
                bucket_hits[bucket][begin] += count

            for bucket in response.data:
                bucket["crash_history"] = [
                    {"begin": begin, "count": count}
                    for begin, count in bucket_hits.get(bucket["id"], {}).items()
                ]

        return response

    def retrieve(self, request, *args, **kwargs):
        user = User.get_or_create_restricted(request.user)[0]
        instance = self.get_object()
        ignore_toolfilter = getattr(self, "ignore_toolfilter", False)

        crashes_in_filter = filter_crash_entries_by_toolfilter(
            request, instance.crashentry_set,
            restricted_only=bool(ignore_toolfilter),
        )
        crashes_in_filter = CrashEntry.deferRawFields(crashes_in_filter)

        if not ignore_toolfilter and not user.restricted:
            # if a non-restricted user requested toolfilter, we ignored it...
            # otherwise if the bucket had no crashes in toolfilter, it would 404
            # recalculate size and quality using toolfilter
            # even if the result is 0
            agg = crashes_in_filter.aggregate(quality=Min("testcase__quality"), size=Count("id"))
            instance.size = agg["size"]
            instance.quality = agg["quality"]

        if instance.quality is not None:
            best_crash = crashes_in_filter.filter(testcase__quality=instance.quality).order_by(
                "testcase__size", "-id"
            ).first()
            instance.best_entry = best_crash.id

        if instance.size:
            latest_crash = crashes_in_filter.order_by("id").last()
            instance.latest_entry = latest_crash.id

        serializer = self.get_serializer(instance)
        response = Response(serializer.data)

        if self.vue and response.status_code == 200:
            hits = filter_bucket_hits_by_toolfilter(
                request,
                BucketHit.objects.all(),
                restricted_only=bool(ignore_toolfilter),
            ).filter(
                begin__gte=timezone.now() - timedelta(days=getattr(django_settings, "CLEANUP_CRASHES_AFTER_DAYS", 14)),
                bucket_id=response.data["id"],
            ).order_by("begin")

            response.data["crash_history"] = list(hits.values("begin", "count"))

        return response

    def __validate(self, request, bucket, submitSave, reassign):
        try:
            bucket.getSignature()
        except RuntimeError as e:
            raise ValidationError('Signature is not valid: %s' % e)

        # Only save if we hit "save" (not e.g. "preview")
        if submitSave:
            if bucket.bug is not None:
                bucket.bug.save()
                # this is not a no-op!
                # if the bug was just created by .save(),
                # it must be re-assigned to the model
                # ref: https://docs.djangoproject.com/en/3.1/topics/db/examples/many_to_one/
                # "Note that you must save an object before it can be
                #  assigned to a foreign key relationship."
                bucket.bug = bucket.bug
            bucket.save()

        inList, outList = [], []
        inListCount, outListCount = 0, 0
        # If the reassign checkbox is checked
        if reassign:
            inList, outList, inListCount, outListCount = bucket.reassign(submitSave)

        # Save bucket and redirect to viewing it
        if submitSave:
            return {
                'url': reverse('crashmanager:sigview', kwargs={'sigid': bucket.pk})
            }

        # Render the preview page
        return {
            'warningMessage': "This is a preview, don't forget to save!",
            'inList': inList,
            'outList': outList,
            'inListCount': inListCount,
            'outListCount': outListCount,
        }

    def update(self, request, *args, **kwargs):
        raise MethodNotAllowed(request.method)

    def partial_update(self, request, *args, **kwargs):
        user = User.get_or_create_restricted(request.user)[0]
        if user.restricted:
            raise MethodNotAllowed(request.method)

        serializer = self.get_serializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        bucket = get_object_or_404(Bucket, id=self.kwargs["pk"])
        check_authorized_for_signature(request, bucket)

        if 'bug' in serializer.validated_data:
            if serializer.validated_data['bug'] is None:
                bug = None
            else:
                bug = Bug.objects.filter(
                    externalId=serializer.validated_data.get('bug')['externalId'],
                    externalType=serializer.validated_data.get('bug_provider'),
                )
                if not bug.exists():
                    bug = Bug(
                        externalId=serializer.validated_data.get('bug')['externalId'],
                        externalType=serializer.validated_data.get('bug_provider'),
                    )
                else:
                    bug = bug.first()

            bucket.bug = bug

        if 'signature' in serializer.validated_data:
            bucket.signature = serializer.validated_data['signature']
        if 'shortDescription' in serializer.validated_data:
            bucket.shortDescription = serializer.validated_data['shortDescription']
        if 'frequent' in serializer.validated_data:
            bucket.frequent = serializer.validated_data['frequent']
        if 'permanent' in serializer.validated_data:
            bucket.permanent = serializer.validated_data['permanent']

        save = request.query_params.get('save', 'true').lower() not in ('false', '0')
        reassign = request.query_params.get('reassign', 'true').lower() not in ('false', '0')
        data = self.__validate(request, bucket, save, reassign)
        return Response(
            status=status.HTTP_200_OK,
            data=data,
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        bucket = Bucket(
            signature=serializer.validated_data.get('signature'),
            shortDescription=serializer.validated_data.get('shortDescription'),
            frequent=serializer.validated_data.get('frequent'),
            permanent=serializer.validated_data.get('permanent')
        )

        save = request.query_params.get('save', 'true').lower() not in ('false', '0')
        reassign = request.query_params.get('reassign', 'true').lower() not in ('false', '0')
        data = self.__validate(request, bucket, save, reassign)
        response_status = status.HTTP_201_CREATED if save else status.HTTP_200_OK
        return Response(
            status=response_status,
            data=data,
        )


class BucketVueViewSet(BucketViewSet):
    """API endpoint that allows viewing Buckets and always uses Vue serializer"""
    def get_serializer(self, *args, **kwds):
        self.vue = True
        return BucketVueSerializer(*args, **kwds)


class BugProviderViewSet(mixins.ListModelMixin,
                         viewsets.GenericViewSet):
    """
    API endpoint that allows listing BugProviders
    """
    authentication_classes = (TokenAuthentication, SessionAuthentication)
    queryset = BugProvider.objects.all()
    serializer_class = BugProviderSerializer


class BugzillaTemplateViewSet(mixins.ListModelMixin,
                              mixins.RetrieveModelMixin,
                              viewsets.GenericViewSet):
    """
    API endpoint that allows viewing BugzillaTemplates
    """
    authentication_classes = (TokenAuthentication, SessionAuthentication)
    queryset = BugzillaTemplate.objects.all()
    serializer_class = BugzillaTemplateSerializer


class NotificationViewSet(mixins.ListModelMixin,
                          viewsets.GenericViewSet):
    """
    API endpoint that allows listing unread Notifications
    """
    authentication_classes = (TokenAuthentication, SessionAuthentication)
    serializer_class = NotificationSerializer
    filter_backends = [JsonQueryFilterBackend, ]

    def get_queryset(self):
        return Notification.objects.unread().filter(recipient=self.request.user)

    @action(detail=True, methods=['patch'])
    def mark_as_read(self, request, pk=None):
        notification = self.get_object()

        if notification.recipient != request.user:
            raise PermissionDenied()

        notification.mark_as_read()
        return Response(status=status.HTTP_200_OK)

    @action(detail=False, methods=['patch'])
    def mark_all_as_read(self, request):
        notifications = self.get_queryset()
        notifications.mark_all_as_read()
        return Response(status=status.HTTP_200_OK)


def json_to_query(json_str):
    """
    This method converts JSON objects into trees of Django Q objects.
    It can be used to provide the user the ability to perform complex
    queries on the database using JSON as a query string.

    The decoded JSON may only contain objects. Each object must contain
    an "op" key that describes the operation of the object. This can either
    be "AND", "OR" or "NOT". Right now, it is mandatory to specify an operator
    even if there is only one element in the object.

    Any other keys in the object are interpreted as follows:

    If the value of the key is an object itself, recursively create a new
    query object and connect all query objects in the current object together
    using the specified operator. In this case, the key itself remains unused.

    If the value of the key is a string, directly interpret key and value as
    a query string for the database.

    If the operator is "NOT", then only one other key can be present in the
    object. If the operator is "AND" or "OR" and only one other key is present,
    then the operator has no effect.
    """
    try:
        obj = json.loads(json_str, object_pairs_hook=OrderedDict)
    except ValueError as e:
        raise RuntimeError("Invalid JSON: %s" % e)

    def get_query_obj(obj, key=None):

        if obj is None or isinstance(obj, (six.text_type, list, int)):
            kwargs = {key: obj}
            qobj = Q(**kwargs)
            return qobj
        elif not isinstance(obj, dict):
            raise RuntimeError("Invalid object type '%s' in query object" % type(obj).__name__)

        qobj = Q()

        if "op" not in obj:
            raise RuntimeError("No operator specified in query object")

        op = obj["op"]
        objkeys = [value for value in obj if value != "op"]

        if op == 'NOT' and len(objkeys) > 1:
            raise RuntimeError("Attempted to negate multiple objects at once")

        for objkey in objkeys:
            if op == 'AND':
                qobj.add(get_query_obj(obj[objkey], objkey), Q.AND)
            elif op == 'OR':
                qobj.add(get_query_obj(obj[objkey], objkey), Q.OR)
            elif op == 'NOT':
                qobj = get_query_obj(obj[objkey], objkey)
                qobj.negate()
            else:
                raise RuntimeError("Invalid operator '%s' specified in query object" % op)

        return qobj

    return (obj, get_query_obj(obj))


class AbstractDownloadView(APIView):
    authentication_classes = (TokenAuthentication, SessionAuthentication)
    permission_classes = (CheckAppPermission,)

    def response(self, file_path, filename, content_type='application/octet-stream'):
        if not os.path.exists(file_path):
            return HttpResponse(status=404)

        test_file = open(file_path, 'rb')
        response = HttpResponse(FileWrapper(test_file), content_type='application/octet-stream')
        response['Content-Disposition'] = 'attachment; filename="%s"' % filename
        return response

    def get(self):
        return HttpResponse(status=500)


class TestDownloadView(AbstractDownloadView):
    def get(self, request, crashid):
        storage_base = getattr(django_settings, 'TEST_STORAGE', None)
        if not storage_base:
            # This is a misconfiguration
            return HttpResponse(status=500)

        entry = get_object_or_404(CrashEntry, pk=crashid)
        check_authorized_for_crash_entry(request, entry)

        if not entry.testcase:
            return HttpResponse(status=404)

        file_path = os.path.join(storage_base, entry.testcase.test.name)
        return self.response(file_path, entry.testcase.test.name)


class SignaturesDownloadView(AbstractDownloadView):
    def get(self, request, format=None):
        deny_restricted_users(request)

        storage_base = getattr(django_settings, 'SIGNATURE_STORAGE', None)
        if not storage_base:
            # This is a misconfiguration
            return HttpResponse(status=500)

        filename = "signatures.zip"
        file_path = os.path.join(storage_base, filename)

        return self.response(file_path, filename)


class BugzillaTemplateListView(ListView):
    model = BugzillaTemplate
    template_name = 'bugzilla/list.html'
    paginate_by = 100


class BugzillaTemplateDeleteView(DeleteView):
    model = BugzillaTemplate
    template_name = 'bugzilla/delete.html'
    success_url = reverse_lazy('crashmanager:templates')
    pk_url_kwarg = 'templateId'


class BugzillaTemplateEditView(UpdateView):
    model = BugzillaTemplate
    template_name = 'bugzilla/create_edit.html'
    success_url = reverse_lazy('crashmanager:templates')
    pk_url_kwarg = 'templateId'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Edit template'
        return context

    def get_form_class(self):
        if self.object.mode == BugzillaTemplateMode.Bug:
            return BugzillaTemplateBugForm
        else:
            return BugzillaTemplateCommentForm


class BugzillaTemplateBugCreateView(CreateView):
    model = BugzillaTemplate
    template_name = 'bugzilla/create_edit.html'
    form_class = BugzillaTemplateBugForm
    success_url = reverse_lazy('crashmanager:templates')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Create a bug template'
        return context

    def form_valid(self, form):
        form.instance.mode = BugzillaTemplateMode.Bug
        return super(BugzillaTemplateBugCreateView, self).form_valid(form)


class BugzillaTemplateCommentCreateView(CreateView):
    model = BugzillaTemplate
    template_name = 'bugzilla/create_edit.html'
    form_class = BugzillaTemplateCommentForm
    success_url = reverse_lazy('crashmanager:templates')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Create a comment template'
        return context

    def form_valid(self, form):
        form.instance.mode = BugzillaTemplateMode.Comment
        return super(BugzillaTemplateCommentCreateView, self).form_valid(form)


class UserSettingsEditView(UpdateView):
    model = User
    template_name = 'usersettings.html'
    form_class = UserSettingsForm
    success_url = reverse_lazy('crashmanager:usersettings')

    def get_form_kwargs(self, **kwargs):
        kwargs = super(UserSettingsEditView, self).get_form_kwargs(**kwargs)
        kwargs['user'] = self.get_queryset().get(user=self.request.user)
        return kwargs

    def get_object(self):
        return self.get_queryset().get(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['bugzilla_providers'] = BugProvider.objects.filter(classname="BugzillaProvider")
        context['user'] = self.request.user
        return context


class InboxView(TemplateView):
    template_name = 'inbox.html'
