from collections import OrderedDict
from datetime import timedelta
from django.core.exceptions import SuspiciousOperation, PermissionDenied
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.db.models import F, Q
from django.db.models.aggregates import Count, Min, Max
from django.http import Http404, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
import functools
import json
import operator
import os
from rest_framework import filters, mixins, viewsets
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from rest_framework.response import Response
from rest_framework.views import APIView
import six

from wsgiref.util import FileWrapper

from FTB.ProgramConfiguration import ProgramConfiguration
from FTB.Signatures.CrashInfo import CrashInfo
from .models import CrashEntry, Bucket, BucketWatch, BugProvider, Bug, Tool, User
from .serializers import InvalidArgumentException, BucketSerializer, CrashEntrySerializer
from server.auth import CheckAppPermission

from django.conf import settings as django_settings


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
        entries = entries.filter(functools.reduce(operator.or_, [Q(("tool", x)) for x in defaultToolsFilter]))
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
        return entries.filter(functools.reduce(operator.or_, [Q(("tool", x)) for x in defaultToolsFilter]))
    elif user.restricted:
        return CrashEntry.objects.none()

    return entries


def filter_signatures_by_toolfilter(request, signatures, restricted_only=False):
    user = User.get_or_create_restricted(request.user)[0]

    if restricted_only and not user.restricted:
        return signatures

    if not user.restricted:
        # If the user is unrestricted and all=1 is set, do not apply any filters
        if "all" in request.GET and request.GET["all"]:
            return signatures

        # Unrestricted users can filter the signature view for a single tool
        if "tool" in request.GET:
            tool_name = request.GET["tool"]
            tool = get_object_or_404(Tool, name=tool_name)
            return signatures.filter(crashentry__tool=tool).distinct()

    defaultToolsFilter = user.defaultToolsFilter.all()
    if defaultToolsFilter:
        return signatures.filter(crashentry__tool__in=defaultToolsFilter).distinct()
    elif user.restricted:
        return Bucket.objects.none()

    return signatures


def renderError(request, err):
    return render(request, 'error.html', {'error_message': err})


def paginate_requested_list(request, entries):
    page_size = request.GET.get('page_size')
    if not page_size:
        page_size = 100
    paginator = Paginator(entries, page_size)
    page = request.GET.get('page')

    try:
        page_entries = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        page_entries = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        page_entries = paginator.page(paginator.num_pages)

    # We need to preserve the query parameters when adding the page to the
    # query URL, so we store the sanitized copy inside our entries object.
    paginator_query = request.GET.copy()
    if 'page' in paginator_query:
        del paginator_query['page']

    page_entries.paginator_query = paginator_query
    page_entries.count = paginator.count

    return page_entries


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

    return render(request, 'stats.html', {'total_reports_per_hour': len(entries), 'frequentBuckets': frequentBuckets})


def settings(request):
    return render(request, 'settings.html')


def allSignatures(request):
    entries = Bucket.objects.annotate(size=Count('crashentry'),
                                      quality=Min('crashentry__testcase__quality')).order_by('-id')
    entries = filter_signatures_by_toolfilter(request, entries, restricted_only=True)
    entries = entries.select_related('bug', 'bug__externalType')
    return render(request, 'signatures/index.html', {'isAll': True, 'siglist': entries})


def watchedSignatures(request):
    # for this user, list watches
    # buckets   sig       new crashes   remove
    # ========================================
    # 1         crash       10          tr
    # 2         assert      0           tr
    # 3         blah        0           tr
    user = User.get_or_create_restricted(request.user)[0]

    # the join of Bucket+CrashEntry is a big one, and each filter() call on a related field adds a join
    # therefore this needs to be a single filter() call, otherwise we get duplicate crashentries in the result
    # this is why tool filtering is done manually here and not using filter_signatures_by_toolfilter()
    defaultToolsFilter = user.defaultToolsFilter.all()
    buckets = Bucket.objects.filter(user=user, crashentry__gt=F('bucketwatch__lastCrash'),
                                    crashentry__tool__in=defaultToolsFilter)
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
    entries = CrashEntry.objects.all().order_by('-id').filter(bucket=bucket, id__gt=watch.lastCrash)
    entries = CrashEntry.deferRawFields(entries)
    entries = filter_crash_entries_by_toolfilter(request, entries)
    latestCrash = CrashEntry.objects.aggregate(latest=Max('id'))['latest']

    data = {'crashlist': paginate_requested_list(request, entries), 'isWatch': True, 'bucket': bucket,
            'latestCrash': latestCrash}

    return render(request, 'crashes/index.html', data)


def signatures(request):
    entries = Bucket.objects.all().order_by('-id')

    filters = {}
    q = None
    isSearch = False

    # These are all keys that are allowed for exact filtering
    exactFilterKeys = [
        "bug__externalId",
        "shortDescription__contains",
        "signature__contains",
        "optimizedSignature__isnull",
    ]

    for key in exactFilterKeys:
        if key in request.GET:
            isSearch = True
            filters[key] = request.GET[key]

    if "q" in request.GET:
        isSearch = True
        q = request.GET["q"]
        entries = entries.filter(
            Q(shortDescription__contains=q) |
            Q(signature__contains=q)
        )

    if "ids" in request.GET:
        isSearch = True
        ids = [int(x) for x in request.GET["ids"].split(",")]
        entries = entries.filter(pk__in=ids)

    # Do not display triaged crash entries unless there is an all=1 parameter
    # specified in the search query. Otherwise only show untriaged entries.
    if ("all" not in request.GET or not request.GET["all"]) and not isSearch:
        filters["bug"] = None

    entries = entries.filter(**filters)

    # Apply default tools filter, only display buckets that contain at least one
    # crash from a tool that we are interested in. Since this query is probably
    # the slowest, it should run after other filters.
    entries = filter_signatures_by_toolfilter(request, entries)

    # Annotate size and quality to each bucket that we're going to display.
    entries = entries.annotate(size=Count('crashentry'), quality=Min('crashentry__testcase__quality'))

    entries = entries.select_related('bug', 'bug__externalType')

    data = {'q': q, 'request': request, 'isSearch': isSearch, 'siglist': entries}
    return render(request, 'signatures/index.html', data)


def crashes(request, ignore_toolfilter=False):
    filters = {}
    q = None
    isSearch = True

    entries = CrashEntry.objects.all().order_by('-id')
    entries = filter_crash_entries_by_toolfilter(request, entries, restricted_only=ignore_toolfilter)

    # These are all keys that are allowed for exact filtering
    exactFilterKeys = [
        "bucket",
        "client__name",
        "client__name__contains",
        "os__name",
        "product__name",
        "product__version",
        "platform__name",
        "testcase__quality",
        "testcase__quality__gt",
        "testcase__quality__lt",
        "tool__name",
        "tool__name__contains",
    ]

    for key in exactFilterKeys:
        if key in request.GET:
            filters[key] = request.GET[key]

    if "sig" in request.GET:
        filters["shortSignature__contains"] = request.GET["sig"]

    if "q" in request.GET:
        q = request.GET["q"]
        entries = entries.filter(
            Q(shortSignature__contains=q) |
            Q(rawStderr__contains=q) |
            Q(rawCrashData__contains=q) |
            Q(args__contains=q)
        )

    # If we don't have any filters up to this point, don't consider it a search
    if not filters and q is None:
        isSearch = False

    # Do not display triaged crash entries unless there is an all=1 parameter
    # specified in the search query. Otherwise only show untriaged entries.
    if "all" not in request.GET or not request.GET["all"]:
        filters["bucket"] = None

    entries = entries.filter(**filters)
    entries = entries.select_related('bucket', 'tool', 'os', 'product', 'platform', 'testcase')
    entries = CrashEntry.deferRawFields(entries)

    data = {
        'q': q,
        'request': request,
        'isAll': ignore_toolfilter,
        'isSearch': isSearch,
        'crashlist': paginate_requested_list(request, entries)
    }

    return render(request, 'crashes/index.html', data)


def queryCrashes(request):
    query = None
    entries = None

    if "query" in request.POST:
        rawQuery = request.POST["query"]
    elif "query" in request.GET:
        rawQuery = request.GET["query"]
    else:
        return render(request, 'crashes/index.html', {'isQuery': True})

    query_lines = rawQuery.splitlines()

    try:
        (obj, query) = json_to_query(rawQuery)
    except RuntimeError as e:
        return render(request, 'crashes/index.html', {'error_message': "Invalid query: %s" % e,
                                                      'query_lines': query_lines, 'isQuery': True})

    # Prettify the raw query for displaying
    rawQuery = json.dumps(obj, indent=2)
    urlQuery = json.dumps(obj, separators=(',', ':'))

    if query:
        entries = CrashEntry.objects.all().order_by('-id').filter(query)
        entries = CrashEntry.deferRawFields(entries)
        entries = filter_crash_entries_by_toolfilter(request, entries)

    # Re-get the lines as we might have reformatted
    query_lines = rawQuery.splitlines()

    data = {'request': request, 'query_lines': query_lines, 'urlQuery': urlQuery, 'isQuery': True, 'crashlist': entries}

    return render(request, 'crashes/index.html', data)


def autoAssignCrashEntries(request):
    entries = CrashEntry.objects.filter(bucket=None).select_related('product', 'platform', 'os', 'testcase')
    buckets = Bucket.objects.all()

    for bucket in buckets:
        signature = bucket.getSignature()
        needTest = signature.matchRequiresTest()

        for entry in entries:
            entry_modified = False

            if not entry.triagedOnce:
                entry.triagedOnce = True
                entry_modified = True

            if signature.matches(entry.getCrashInfo(attachTestcase=needTest)):
                entry.bucket = bucket
                entry_modified = True

            if entry_modified:
                entry.save(update_fields=['bucket', 'triagedOnce'])

    # This query ensures that all issues that have been bucketed manually before
    # the server had a chance to triage them will have their triageOnce flag set,
    # so the hourglass in the UI isn't displayed anymore.
    CrashEntry.objects.exclude(bucket=None).update(triagedOnce=True)

    return redirect('crashmanager:crashes')


def viewCrashEntry(request, crashid):
    entry = get_object_or_404(CrashEntry, pk=crashid)
    check_authorized_for_crash_entry(request, entry)
    entry.deserializeFields()

    if entry.testcase and not entry.testcase.isBinary:
        entry.testcase.loadTest()

    return render(request, 'crashes/view.html', {'entry': entry})


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


def __handleSignaturePost(request, bucket):
    # This method contains code shared between newSignature and editSignature
    # and handles the POST request processing after the bucket object has been
    # either fetched or created.
    try:
        signature = bucket.getSignature()
    except RuntimeError as e:
        data = {'bucket': bucket, 'error_message': 'Signature is not valid: %s' % e}
        return render(request, 'signatures/edit.html', data)

    submitSave = bool('submit_save' in request.POST)

    # Only save if we hit "save" (not e.g. "preview")
    if submitSave:
        bucket.save()

    # If the reassign checkbox is checked, assign all unassigned issues that match
    # our signature to this bucket. Furthermore, remove all non-matching issues
    # from our bucket.
    #
    # Again, we only actually save if we hit "save". For previewing, we just count
    # how many issues would be assigned and removed.
    if 'reassign' in request.POST:
        inList, outList = [], []
        inListCount, outListCount = 0, 0

        signature = bucket.getSignature()
        needTest = signature.matchRequiresTest()
        entries = CrashEntry.objects.filter(Q(bucket=None) | Q(bucket=bucket))
        entries = entries.select_related('product', 'platform', 'os')  # these are used by getCrashInfo
        if needTest:
            entries = entries.select_related('testcase')

        requiredOutputs = signature.getRequiredOutputSources()
        entries = CrashEntry.deferRawFields(entries, requiredOutputs)

        if not submitSave:
            entries = entries.select_related('tool').order_by('-id')  # used by the preview list

        # If we are saving, we only care about the id of each entry
        # Otherwise, we save the entire object. Limit to the first 100 entries to avoid OOM.
        entriesOffset = 0
        while True:
            entriesChunk = entries[entriesOffset:entriesOffset + 100]
            if not entriesChunk:
                break
            entriesOffset += 100
            for entry in entriesChunk:
                match = signature.matches(entry.getCrashInfo(attachTestcase=needTest,
                                                             requiredOutputSources=requiredOutputs))
                if match and entry.bucket_id is None:
                    if submitSave:
                        inList.append(entry.pk)
                    elif len(inList) < 100:
                        inList.append(entry)
                    inListCount += 1
                elif not match and entry.bucket_id is not None:
                    if submitSave:
                        outList.append(entry.pk)
                    elif len(outList) < 100:
                        outList.append(entry)
                    outListCount += 1

        if submitSave:
            while inList:
                updList, inList = inList[:500], inList[500:]
                CrashEntry.objects.filter(pk__in=updList).update(bucket=bucket)
            while outList:
                updList, outList = outList[:500], outList[500:]
                CrashEntry.objects.filter(pk__in=updList).update(bucket=None, triagedOnce=False)

    # Save bucket and redirect to viewing it
    if submitSave:
        return redirect('crashmanager:sigview', sigid=bucket.pk)

    # Render the preview page
    data = {
        'bucket': bucket,
        'error_message': "This is a preview, don't forget to save!",
        'inList': inList, 'outList': outList,
        'inListCount': inListCount, 'outListCount': outListCount,
    }
    return render(request, 'signatures/edit.html', data)


def newSignature(request):
    if request.method == 'POST':
        # TODO: FIXME: Update bug here as well
        bucket = Bucket(
            signature=request.POST['signature'],
            shortDescription=request.POST['shortDescription'],
            frequent="frequent" in request.POST,
            permanent="permanent" in request.POST
        )
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

            data = {'new': True, 'bucket': {
                    'pk': None,
                    'bug': None,
                    'signature': proposedSignature,
                    'shortDescription': proposedShortDesc
                    },
                    'error_message': errorMsg
                    }
        else:
            data = {'new': True}
    else:
        raise SuspiciousOperation

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
    bucket = Bucket.objects.filter(pk=sigid).annotate(size=Count('crashentry'),
                                                      quality=Min('crashentry__testcase__quality'))

    if not bucket:
        raise Http404

    bucket = bucket[0]

    check_authorized_for_signature(request, bucket)

    entries = CrashEntry.objects.filter(bucket=sigid).filter(
        testcase__quality=bucket.quality).order_by('testcase__size', '-id')
    entries = filter_crash_entries_by_toolfilter(request, entries, restricted_only=True)
    entries = entries.values_list('pk', flat=True)[:1]

    bucket.bestEntry = None
    if entries:
        bucket.bestEntry = CrashEntry.objects.select_related('testcase').get(pk=entries[0])

    latestCrash = CrashEntry.objects.aggregate(latest=Max('id'))['latest']

    # standardize formatting of the signature
    bucket.signature = json.dumps(json.loads(bucket.signature), indent=2, sort_keys=True)

    return render(request, 'signatures/view.html', {'bucket': bucket, 'latestCrash': latestCrash})


def editSignature(request, sigid):
    if request.method == 'POST':
        bucket = get_object_or_404(Bucket, pk=sigid)
        check_authorized_for_signature(request, bucket)

        bucket.signature = request.POST['signature']
        bucket.shortDescription = request.POST['shortDescription']
        bucket.frequent = "frequent" in request.POST
        bucket.permanent = "permanent" in request.POST

        # TODO: FIXME: Update bug here as well
        return __handleSignaturePost(request, bucket)
    if request.method == 'GET':
        if sigid is not None:
            bucket = get_object_or_404(Bucket, pk=sigid)
            check_authorized_for_signature(request, bucket)

            if 'fit' in request.GET:
                entry = get_object_or_404(CrashEntry, pk=request.GET['fit'])
                bucket.signature = bucket.getSignature().fit(entry.getCrashInfo())
            else:
                # standardize formatting of the signature
                # this is the same format returned by `fit()`
                bucket.signature = json.dumps(json.loads(bucket.signature), indent=2, sort_keys=True)

            return render(request, 'signatures/edit.html', {'bucket': bucket})
    raise SuspiciousOperation


def linkSignature(request, sigid):
    bucket = get_object_or_404(Bucket, pk=sigid)
    check_authorized_for_signature(request, bucket)

    providers = BugProvider.objects.all()

    data = {'bucket': bucket, 'providers': providers}

    if request.method == 'POST':
        provider = get_object_or_404(BugProvider, pk=request.POST['provider'])
        bugId = request.POST['bugId']
        username = request.POST['username']
        password = request.POST['password']

        bug = Bug.objects.filter(externalId=bugId, externalType=provider)

        if 'submit_save' in request.POST:
            if not bug:
                bug = Bug(externalId=bugId, externalType=provider)
                bug.save()
            else:
                bug = bug[0]

            bucket.bug = bug
            bucket.save()
            return redirect('crashmanager:sigview', sigid=bucket.pk)
        else:
            # This is a preview request
            bugData = provider.getInstance().getBugData(bugId, username, password)

            if bugData is None:
                data['error_message'] = 'Bug not found in external database.'
            else:
                data['summary'] = bugData['summary']

            data['provider'] = provider
            data['bugId'] = bugId
            data['username'] = username

            return render(request, 'signatures/link.html', data)
    elif request.method == 'GET':
        return render(request, 'signatures/link.html', data)
    else:
        raise SuspiciousOperation


def unlinkSignature(request, sigid):
    bucket = get_object_or_404(Bucket, pk=sigid)
    check_authorized_for_signature(request, bucket)

    if request.method == 'POST':
        bucket.bug = None
        bucket.save(update_fields=['bug'])
        return redirect('crashmanager:sigview', sigid=bucket.pk)
    elif request.method == 'GET':
        return render(request, 'signatures/unlink.html', {'bucket': bucket})
    else:
        raise SuspiciousOperation


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

    if request.method == 'POST':
        provider = get_object_or_404(BugProvider, pk=request.POST['provider'])

        # Let the provider handle the POST request, which will file the bug
        # and return us the external bug ID
        extBugId = provider.getInstance().handlePOSTCreate(request, entry)

        # Now create a bug in our database with that ID and assign it to the bucket
        extBug = Bug(externalId=extBugId, externalType=provider)
        extBug.save()
        entry.bucket.bug = extBug
        entry.bucket.save(update_fields=['bug'])

        return redirect('crashmanager:sigview', sigid=entry.bucket.pk)
    elif request.method == 'GET':
        if 'provider' in request.GET:
            provider = get_object_or_404(BugProvider, pk=request.GET['provider'])
        else:
            user = User.get_or_create_restricted(request.user)[0]
            provider = get_object_or_404(BugProvider, pk=user.defaultProviderId)

        return provider.getInstance().renderContextCreate(request, entry)
    else:
        raise SuspiciousOperation


def createExternalBugComment(request, crashid):
    entry = get_object_or_404(CrashEntry, pk=crashid)
    check_authorized_for_crash_entry(request, entry)

    if request.method == 'POST':
        provider = get_object_or_404(BugProvider, pk=request.POST['provider'])
        provider.getInstance().handlePOSTComment(request, entry)
        return redirect('crashmanager:crashview', crashid=crashid)
    elif request.method == 'GET':
        if 'provider' in request.GET:
            provider = get_object_or_404(BugProvider, pk=request.GET['provider'])
        else:
            user = User.get_or_create_restricted(request.user)[0]
            provider = get_object_or_404(BugProvider, pk=user.defaultProviderId)

        return provider.getInstance().renderContextComment(request, entry)
    else:
        raise SuspiciousOperation


def createBugTemplate(request, providerId):
    provider = get_object_or_404(BugProvider, pk=providerId)
    if request.method == 'POST':
        # Let the provider handle the template creation
        templateId = provider.getInstance().handlePOSTCreateEditTemplate(request)

        return redirect('crashmanager:viewtemplate', providerId=provider.pk, templateId=templateId)
    elif request.method == 'GET':
        return provider.getInstance().renderContextCreateTemplate(request)
    else:
        raise SuspiciousOperation


def viewEditBugTemplate(request, providerId, templateId, mode):
    provider = get_object_or_404(BugProvider, pk=providerId)
    if request.method == 'GET':
        return provider.getInstance().renderContextViewTemplate(request, templateId, mode)
    elif request.method == 'POST':
        templateId = provider.getInstance().handlePOSTCreateEditTemplate(request)
        return provider.getInstance().renderContextViewTemplate(request, templateId, mode)


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


def userSettings(request):
    user = User.get_or_create_restricted(request.user)[0]

    def createUserSettingsData(user, msg=None):
        tools = Tool.objects.all()
        currentToolsFilter = user.defaultToolsFilter.all()

        for tool in tools:
            tool.checked = tool in currentToolsFilter

        providers = BugProvider.objects.all()
        provider = providers.filter(pk=user.defaultProviderId)
        templates = None
        if provider:
            provider = provider[0]
            templates = provider.getInstance().getTemplateList()

        return {
            "user": user,
            "tools": tools,
            "providers": providers,
            "templates": templates,
            "defaultProviderId": user.defaultProviderId,
            "defaultTemplateId": user.defaultTemplateId,
            "msg": msg,
        }

    if request.method == 'POST':
        if "changefilter" in request.POST:
            if user.restricted:
                raise PermissionDenied({"message": "You don't have permission to change your tools filter."})
            user.defaultToolsFilter.set([Tool.objects.get(
                name=x.replace("tool_", "", 1)) for x in request.POST if x.startswith("tool_")],
                clear=True)
            data = createUserSettingsData(user, msg="Tools filter updated successfully.")
        elif "changetemplate" in request.POST:
            user.defaultProviderId = int(request.POST['defaultProvider'])
            user.defaultTemplateId = int(request.POST['defaultTemplate'])
            user.save()
            data = createUserSettingsData(user, msg="Default provider/template updated successfully.")
        else:
            raise SuspiciousOperation

        return render(request, 'usersettings.html', data)
    elif request.method == 'GET':
        return render(request, 'usersettings.html', createUserSettingsData(user))
    else:
        raise SuspiciousOperation


class JsonQueryFilterBackend(filters.BaseFilterBackend):
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
            except RuntimeError as e:
                raise InvalidArgumentException("error in query: %s" % e)
            queryset = queryset.filter(queryobj)
        return queryset


class BucketAnnotateFilterBackend(filters.BaseFilterBackend):
    """
    Annotates bucket queryset with size and best_quality
    """
    def filter_queryset(self, request, queryset, view):
        # we should use a subquery to get best_quality which would allow us to also get the corresponding crash
        # Subquery was added in Django 1.11
        return queryset.annotate(size=Count('crashentry'), quality=Min('crashentry__testcase__quality'))


class CrashEntryViewSet(mixins.CreateModelMixin,
                        mixins.RetrieveModelMixin,
                        viewsets.GenericViewSet):
    """
    API endpoint that allows adding/viewing CrashEntries
    """
    authentication_classes = (TokenAuthentication,)
    queryset = CrashEntry.objects.all().select_related('product', 'platform', 'os', 'client', 'tool', 'testcase')
    serializer_class = CrashEntrySerializer
    filter_backends = [JsonQueryFilterBackend]

    def retrieve(self, request, *args, **kwargs):
        deny_restricted_users(request)
        return super(CrashEntryViewSet, self).retrieve(request, *args, **kwargs)

    def list(self, request, *args, **kwargs):
        """
        Based on ListModelMixin.list()
        """
        deny_restricted_users(request)

        queryset = self.filter_queryset(self.get_queryset())

        include_raw = request.query_params.get('include_raw', '1')
        try:
            include_raw = int(include_raw)
            assert include_raw in {0, 1}
        except (AssertionError, ValueError):
            raise InvalidArgumentException({'include_raw': ['Expecting 0 or 1.']})

        if not include_raw:
            queryset = queryset.defer('rawStdout', 'rawStderr', 'rawCrashData')

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, include_raw=include_raw, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, include_raw=include_raw, many=True)
        return Response(serializer.data)

    def partial_update(self, request, pk=None):
        """
        Update individual crash fields.
        """
        deny_restricted_users(request)

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


class BucketViewSet(mixins.ListModelMixin,
                    mixins.RetrieveModelMixin,
                    viewsets.GenericViewSet):
    """
    API endpoint that allows viewing Buckets
    """
    authentication_classes = (TokenAuthentication,)
    queryset = Bucket.objects.all().select_related('bug')
    serializer_class = BucketSerializer
    filter_backends = [BucketAnnotateFilterBackend, JsonQueryFilterBackend]

    def retrieve(self, request, *args, **kwargs):
        deny_restricted_users(request)
        return super(BucketViewSet, self).retrieve(request, *args, **kwargs)

    def list(self, request, *args, **kwargs):
        deny_restricted_users(request)
        return super(BucketViewSet, self).list(request, *args, **kwargs)


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
