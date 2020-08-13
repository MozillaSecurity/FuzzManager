from django.conf import settings
from django.core.exceptions import SuspiciousOperation, PermissionDenied
from django.db.models import Q
from django.http import Http404
from django.http.response import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
import json
import os
from rest_framework import mixins, viewsets, filters
from rest_framework.authentication import TokenAuthentication, \
    SessionAuthentication
from wsgiref.util import FileWrapper

from server.views import JsonQueryFilterBackend, SimpleQueryFilterBackend

from .models import Collection, Repository, ReportConfiguration, ReportSummary, Report
from .serializers import CollectionSerializer, RepositorySerializer, ReportConfigurationSerializer, ReportSerializer
from .tasks import aggregate_coverage_data, calculate_report_summary
from crashmanager.models import Tool

from .SourceCodeProvider import SourceCodeProvider


def index(request):
    return redirect('covmanager:%s' % getattr(settings, 'COV_DEFAULT_PAGE', "collections"))


def reports(request):
    return render(request, 'collections/report.html', {})


def repositories(request):
    repositories = Repository.objects.all()
    return render(request, 'repositories/index.html', {'repositories': repositories})


def reportconfigurations(request):
    return render(request, 'reportconfigurations/index.html', {})


def collections(request):
    return render(request, 'collections/index.html', {})


def collections_browse(request, collectionid):
    return render(request, 'collections/browse.html', {'collectionid': collectionid})


def collections_diff(request):
    return render(request, 'collections/browse.html', {'diff_api': True})


def collections_reportsummary(request, collectionid):
    return render(request, 'reportconfigurations/summary.html', {'collectionid': collectionid})


def collections_reportsummary_html_list(request, collectionid):
    collection = get_object_or_404(Collection, pk=collectionid)

    if not collection.coverage:
        return HttpResponse(
            content=json.dumps({"error": "Specified collection is not ready yet."}),
            content_type='application/json',
            status=400
        )

    if not hasattr(collection, 'reportsummary'):
        return HttpResponse(
            content=json.dumps({"message": "The requested collection has no report summary."}),
            content_type='application/json',
            status=400
        )

    if not collection.reportsummary.cached_result:
        return HttpResponse(
            content=json.dumps({"message": "The requested report summary is currently being created."}),
            content_type='application/json',
            status=204
        )

    root = json.loads(collection.reportsummary.cached_result)
    root["cid"] = collectionid

    if "diff" in request.GET:
        diff_collection = get_object_or_404(Collection, pk=request.GET["diff"])

        if not diff_collection.coverage:
            return HttpResponse(
                content=json.dumps({"error": "Specified diff collection is not ready yet."}),
                content_type='application/json',
                status=400
            )

        if not hasattr(diff_collection, 'reportsummary'):
            return HttpResponse(
                content=json.dumps({"message": "The requested diff collection has no report summary."}),
                content_type='application/json',
                status=400
            )

        if not diff_collection.reportsummary.cached_result:
            return HttpResponse(
                content=json.dumps({"message": "The requested diff report summary is currently being created."}),
                content_type='application/json',
                status=204
            )

        root["diffid"] = diff_collection.pk

        def annotate_delta(a, b):
            delta = round(a["coveragePercent"] - b["coveragePercent"], 2)

            if delta >= 1.0:
                a["coveragePercentDelta"] = "+%s %%" % delta
            elif delta <= -1.0:
                a["coveragePercentDelta"] = "%s %%" % delta

            if "children" not in a or "children" not in b:
                return

            # Map children to their ids so we can iterate them side-by-side
            a_child_dict = {c["id"]: c for c in a["children"]}
            b_child_dict = {c["id"]: c for c in b["children"]}

            for id in a_child_dict:
                # The id might not be in the second report
                if id in b_child_dict:
                    annotate_delta(a_child_dict[id], b_child_dict[id])
                else:
                    a_child_dict[id]["coveragePercentDelta"] = "new"

        diff = json.loads(diff_collection.reportsummary.cached_result)
        annotate_delta(root, diff)

    return render(request, 'reportconfigurations/summary_html_list.html', {'root': root})


def collections_download(request, collectionid):
    collection = get_object_or_404(Collection, pk=collectionid)

    if not collection.coverage:
        return HttpResponse(
            content=json.dumps({"message": "The requested collection is currently being created."}),
            content_type='application/json',
            status=204
        )

    cov_file = open(collection.coverage.file.path, 'rb')
    response = HttpResponse(FileWrapper(cov_file), content_type='application/octet-stream')
    response['Content-Disposition'] = 'attachment; filename="%s"' % os.path.basename(collection.coverage.file.path)
    return response


def collections_browse_api(request, collectionid, path):
    collection = get_object_or_404(Collection, pk=collectionid)

    if not collection.coverage:
        return HttpResponse(
            content=json.dumps({"message": "The requested collection is currently being created."}),
            content_type='application/json',
            status=204
        )

    report_configuration = None
    if "rc" in request.GET:
        report_configuration = get_object_or_404(ReportConfiguration, pk=request.GET["rc"])

    coverage = collection.subset(path, report_configuration)

    if not coverage:
        raise Http404("Path not found.")

    if "children" in coverage:
        # Viewing a directory, so we should remove detailed coverage
        # information before returning this data.
        Collection.strip(coverage)
    else:
        # This is a leaf, we need to add source code
        collection.annotateSource(path, coverage)

    data = {"path": path, "coverage": coverage}
    return HttpResponse(json.dumps(data), content_type='application/json')


def collections_diff_api(request, path):

    collections = None
    coverages = []

    if "ids" in request.GET:
        ids = request.GET["ids"].split(",")
        collections = Collection.objects.filter(pk__in=ids)

    if len(collections) < 2:
        raise Http404("Need at least two collections")

    report_configuration = None
    if "rc" in request.GET:
        report_configuration = get_object_or_404(ReportConfiguration, pk=request.GET["rc"])

    # coverage = collection.subset(path)

    # if "children" in coverage:
    #    # Viewing a directory, so we should remove detailed coverage
    #    # information before returning this data.
    #    Collection.strip(coverage)
    # else:
    #    raise Http404("NYI")

    tooltipdata = []

    for collection in collections:
        if not collection.coverage:
            return HttpResponse(
                content=json.dumps({"error": "One of the specified collections is not ready yet."}),
                content_type='application/json',
                status=400
            )

        coverage = collection.subset(path, report_configuration)

        if "children" in coverage:
            Collection.remove_childrens_children(coverage)

            # Viewing a directory, so we should remove detailed coverage
            # information before returning this data.
            Collection.strip(coverage)
        else:
            # TODO: Check if the source file is identical in each collection
            # If so, we can display it. If not, we should not annotate for now.
            # collection.annotateSource(path, coverage)
            raise Http404("NYI")

        if not coverage:
            raise Http404("Path not found.")

        coverages.append(coverage)

        ctooltipdata = {}
        for k in coverage:
            if k != "children":
                ctooltipdata[k] = coverage[k]

        ctooltipdata["id"] = collection.pk
        ctooltipdata["label"] = "No description"
        ctooltipdata["created"] = collection.created.strftime("%b. %-d %Y %-I:%M %p")
        if collection.description:
            ctooltipdata["label"] = collection.description

        if tooltipdata:
            # Store deltas to previous data points
            for k in tooltipdata[-1]:
                if k not in ctooltipdata:
                    continue

                x = tooltipdata[-1][k]
                if type(x) == int:
                    ctooltipdata["delta_" + k] = ctooltipdata[k] - x
                elif type(x) == float:
                    ctooltipdata["delta_" + k] = round(ctooltipdata[k] - x, 4)

        tooltipdata.append(ctooltipdata)

    start_coverage = coverages[0]
    end_coverage = coverages[-1]

    add = {}
    for k in start_coverage:
        if type(start_coverage[k]) == int:
            add["delta_" + k] = end_coverage[k] - start_coverage[k]
        elif type(start_coverage[k]) == float:
            add["delta_" + k] = round(end_coverage[k] - start_coverage[k], 4)
    start_coverage.update(add)

    for child in start_coverage["children"]:
        add = {}

        if child not in end_coverage["children"]:
            continue

        for k in start_coverage["children"][child]:
            x = start_coverage["children"][child][k]

            if type(x) == int:
                add["delta_" + k] = end_coverage["children"][child][k] - x
            elif type(x) == float:
                add["delta_" + k] = round(end_coverage["children"][child][k] - x, 4)
        start_coverage["children"][child].update(add)

    data = {"path": path, "coverage": start_coverage, "ttdata": tooltipdata}
    return HttpResponse(json.dumps(data), content_type='application/json')


def collections_patch(request):
    return render(request, 'collections/patch.html', {})


def collections_patch_api(request, collectionid, patch_revision):
    collection = get_object_or_404(Collection, pk=collectionid)

    if not collection.coverage:
        return HttpResponse(
            content=json.dumps({"error": "Specified collection is not ready yet."}),
            content_type='application/json',
            status=400
        )

    prepatch = "prepatch" in request.GET

    provider = collection.repository.getInstance()

    diff_revision = patch_revision
    if prepatch:
        parents = provider.getParents(patch_revision)

        if not parents:
            raise Http404("Revision has no parents")

        diff_revision = parents[0]

    diff = SourceCodeProvider.Utils.getDiffLocations(provider.getUnifiedDiff(patch_revision))

    total_locations = 0
    total_missed = 0

    for obj in diff:
        filename = obj["filename"]
        locations = obj["locations"]

        prepatch_source = provider.getSource(filename, diff_revision)
        coll_source = provider.getSource(filename, collection.revision)

        if prepatch_source != coll_source:
            response = {"error": "Source code mismatch."}
            response["filename"] = filename
            response["prepatch_source"] = prepatch_source
            response["coll_source"] = coll_source
            return HttpResponse(json.dumps(response), content_type='application/json')

        (basepath, basename) = os.path.split(filename)
        coverage = collection.subset(basepath)["children"][basename]["coverage"]

        missed_locations = []
        not_coverable = []

        for idx in range(0, len(locations)):
            location = locations[idx]
            if location > 0 and location < len(coverage):
                if coverage[location] == 0:
                    missed_locations.append(location)
                elif coverage[location] < 0:
                    if not prepatch:
                        not_coverable.append(location)
                        continue

                    # The location specified isn't coverable. We should try to
                    # find the next coverable location within a certain range
                    # that isn't on our list anyway.

                    plus_offset = None
                    minus_offset = None

                    # Maximum offset chosen by fair dice roll
                    for offset in range(1, 4):
                        if location + offset in locations:
                            break

                        if location + offset < len(coverage) and coverage[location + offset] >= 0:
                            plus_offset = offset
                            break

                    for offset in range(1, 4):
                        if location - offset in locations:
                            break

                        if location - offset >= 0 and coverage[location - offset] >= 0:
                            minus_offset = offset
                            break

                    if plus_offset:
                        if minus_offset:
                            if plus_offset >= minus_offset:
                                locations[idx] = location - offset
                            else:
                                locations[idx] = location + offset
                        else:
                            locations[idx] = location + offset
                    elif minus_offset:
                        locations[idx] = location - offset
                    else:
                        # We couldn't find any code close to this that is coverable,
                        # so we have to consider this code uncoverable and ignore the
                        # location entirely.
                        not_coverable.append(location)

                    if coverage[locations[idx]] == 0:
                        missed_locations.append(locations[idx])

        locations = [x for x in locations if x not in not_coverable]

        obj["missed"] = missed_locations
        obj["locations"] = locations
        obj["not_coverable"] = not_coverable

        total_locations += len(locations)
        total_missed += len(missed_locations)

    results = {
        "total_locations": total_locations,
        "total_missed": total_missed,
        "percentage_missed": round(((float(total_missed) / total_locations) * 100), 2),
        "results": diff
    }

    return HttpResponse(json.dumps(results), content_type='application/json')


def collections_reportsummary_api(request, collectionid):
    collection = get_object_or_404(Collection, pk=collectionid)

    if not collection.coverage:
        return HttpResponse(
            content=json.dumps({"error": "Specified collection is not ready yet."}),
            content_type='application/json',
            status=400
        )

    task_scheduled = False

    if not hasattr(collection, 'reportsummary'):
        summary = ReportSummary(collection=collection, cached_result=None)
        summary.save()
        calculate_report_summary.delay(summary.pk)
        task_scheduled = True
    else:
        summary = collection.reportsummary

    if request.method == 'POST':
        # This is a refresh request
        if not task_scheduled:
            summary.cached_result = None
            summary.save()
            calculate_report_summary.delay(summary.pk)
        return HttpResponse(content=json.dumps({"msg": "Success"}))

    if not summary.cached_result:
        return HttpResponse(
            content=json.dumps({"message": "The requested collection is currently being created."}),
            content_type='application/json',
            status=204
        )

    return HttpResponse(summary.cached_result, content_type='application/json')


def repositories_search_api(request):
    results = []

    if "name" in request.GET:
        name = request.GET["name"]
        results = Repository.objects.filter(name__contains=name).values_list('name', flat=True)

    return HttpResponse(json.dumps({"results": list(results)}), content_type='application/json')


def tools_search_api(request):
    results = []

    if "name" in request.GET:
        name = request.GET["name"]
        results = Tool.objects.filter(name__contains=name).values_list('name', flat=True)

    return HttpResponse(json.dumps({"results": list(results)}), content_type='application/json')


@csrf_exempt
def collections_aggregate_api(request):
    if request.method != 'POST':
        return HttpResponse(
            content=json.dumps({"error": "This API only supports POST."}),
            content_type='application/json',
            status=400
        )

    if not request.is_ajax():
        raise SuspiciousOperation

    data = json.loads(request.body)

    collections = None

    if "ids" in data:
        ids = data["ids"].split(",")
        collections = Collection.objects.filter(pk__in=ids)

    if not collections or len(collections) < 2:
        return HttpResponse(
            content=json.dumps({"error": "Need at least two collections to aggregate."}),
            content_type='application/json',
            status=400
        )

    for collection in collections:
        if not collection.coverage:
            return HttpResponse(
                content=json.dumps({"error": "One of the specified collections is not ready yet."}),
                content_type='application/json',
                status=400
            )

    provider = collections[0].repository.getInstance()

    # Basic aggregation checks: Repository, revision and branch must match
    for collection in collections[1:]:
        if collection.repository != collections[0].repository:
            return HttpResponse(
                content=json.dumps({"error": "Specified collections are based on different repositories."}),
                content_type='application/json',
                status=400
            )

        if not provider.checkRevisionsEquivalent(collection.revision, collections[0].revision):
            return HttpResponse(
                content=json.dumps({"error": "Specified collections are based on different revisions."}),
                content_type='application/json',
                status=400
            )

        if collection.branch != collections[0].branch:
            return HttpResponse(
                content=json.dumps({"error": "Specified collections are based on different branches."}),
                content_type='application/json',
                status=400
            )

    # We allow either a new description to be specified or to auto-aggregate all existing descriptions
    description = None
    descriptions = None
    if "description" in data:
        description = data["description"]
    else:
        descriptions = [collections[0].description]

    mergedCollection = Collection()

    # Start out with the values of the first collection
    mergedCollection.repository = collections[0].repository
    mergedCollection.revision = collections[0].revision
    mergedCollection.branch = collections[0].branch
    mergedCollection.client = collections[0].client

    if description:
        mergedCollection.description = description

    for collection in collections[1:]:
        # If we are aggregating descriptions, store it for later
        if descriptions:
            descriptions.append(collection.description)

        # Prefer long revision hashes over short
        if len(collection.revision) > len(mergedCollection.revision):
            mergedCollection.revision = collection.revision

    if descriptions:
        mergedCollection.description = " | ".join(descriptions)

    # Save the collection without coverage data for now
    mergedCollection.coverage = None
    mergedCollection.save()

    # New set of tools is the combination of all tools involved
    tools = []
    for collection in collections:
        tools.extend(collection.tools.all())
    mergedCollection.tools.add(*tools)

    aggregate_coverage_data.delay(mergedCollection.pk, ids)

    return HttpResponse(content=json.dumps({"newid": mergedCollection.pk}), content_type='application/json')


class CollectionFilterBackend(filters.BaseFilterBackend):
    """
    Accepts filtering with several collection-specific fields from the URL
    """
    def filter_queryset(self, request, queryset, view):
        """
        Return a filtered queryset.
        """
        # Return early on empty queryset
        if not queryset:
            return queryset

        filters = {}
        exactFilterKeys = [
            "description__contains",
            "repository__name",
            "repository__name__contains",
            "revision",
            "revision__contains",
            "branch",
            "branch__contains",
            "tools__name",
            "tools__name__contains",
        ]

        for key in exactFilterKeys:
            if key in request.GET:
                val = request.query_params.get(key, None)
                if val:
                    filters[key] = val

        if "ids" in request.GET:
            val = request.query_params.get("ids", None)
            if val:
                filters["pk__in"] = val.split(',')

        if filters:
            queryset = queryset.filter(**filters).distinct()

        return queryset.order_by('-pk')


class CollectionViewSet(mixins.CreateModelMixin,
                        mixins.ListModelMixin,
                        mixins.RetrieveModelMixin,
                        viewsets.GenericViewSet):
    """
    API endpoint that allows adding/viewing Collections
    """
    authentication_classes = (TokenAuthentication, SessionAuthentication)
    queryset = Collection.objects.all()
    serializer_class = CollectionSerializer
    paginate_by_param = 'limit'
    filter_backends = [
        JsonQueryFilterBackend,
        SimpleQueryFilterBackend,
        CollectionFilterBackend
    ]


class ReportFilterBackend(filters.BaseFilterBackend):
    """
    Accepts broad filtering by q parameter to search multiple fields
    """
    def filter_queryset(self, request, queryset, view):
        """
        Return a filtered queryset.
        """
        # Return early on empty queryset
        if not queryset:
            return queryset

        can_see_unpublished = False
        if request.user and request.user.is_authenticated:
            can_see_unpublished = request.user.has_perm('crashmanager.view_crashmanager')

        # We allow users to see unpublished reports, if they ask for it
        # and also have the permissions to do so.
        unpublished_requested = request.method != 'GET' or "unpublished" in request.GET

        # The regular collection/browse view should be able to fetch optional
        # report metadata limited to one or more collections.
        if request.method == 'GET' and "coverage__ids" in request.GET:
            coverage_ids = request.GET["coverage__ids"].split(",")
            queryset = queryset.filter(coverage_id__in=coverage_ids)

        # TODO: Right now we use the view_crashmanager permission because that
        # typically indicates full/internal access. But in the future, this
        # might be replaced by its own permission.
        if not unpublished_requested or not can_see_unpublished:
            queryset = queryset.filter(public=True)

        return queryset.order_by('-pk')


class ReportViewSet(mixins.UpdateModelMixin,
                    mixins.ListModelMixin,
                    mixins.RetrieveModelMixin,
                    viewsets.GenericViewSet):
    """
    API endpoint that allows viewing Reports
    """
    authentication_classes = (TokenAuthentication, SessionAuthentication)
    queryset = Report.objects.all()
    serializer_class = ReportSerializer
    paginate_by_param = 'limit'
    filter_backends = [ReportFilterBackend]

    def partial_update(self, request, *args, **kwargs):
        if (not request.user or not request.user.is_authenticated or
                not request.user.has_perm('crashmanager.view_crashmanager')):
            raise PermissionDenied()

        return super(ReportViewSet, self).partial_update(request, *args, **kwargs)


class RepositoryViewSet(mixins.ListModelMixin,
                        mixins.RetrieveModelMixin,
                        viewsets.GenericViewSet):
    """
    API endpoint that allows viewing Repositories
    """
    authentication_classes = (TokenAuthentication,)
    queryset = Repository.objects.all()
    serializer_class = RepositorySerializer
    filter_backends = [JsonQueryFilterBackend]


class ReportConfigurationFilterBackend(filters.BaseFilterBackend):
    """
    Accepts broad filtering by q parameter to search multiple fields
    """
    def filter_queryset(self, request, queryset, view):
        """
        Return a filtered queryset.
        """
        # Return early on empty queryset
        if not queryset:
            return queryset

        q = request.query_params.get("q", None)
        if q:
            queryset = queryset.filter(
                Q(description__contains=q) |
                Q(repository__name__contains=q) |
                Q(directives__contains=q)
            )

        return queryset.order_by('-pk')


class ReportConfigurationViewSet(mixins.CreateModelMixin,
                                 mixins.UpdateModelMixin,
                                 mixins.ListModelMixin,
                                 mixins.RetrieveModelMixin,
                                 viewsets.GenericViewSet):
    """
    API endpoint that allows adding/updating/viewing Report Configurations
    """
    authentication_classes = (TokenAuthentication, SessionAuthentication)
    queryset = ReportConfiguration.objects.all()
    serializer_class = ReportConfigurationSerializer
    filter_backends = [JsonQueryFilterBackend, SimpleQueryFilterBackend, ReportConfigurationFilterBackend]
