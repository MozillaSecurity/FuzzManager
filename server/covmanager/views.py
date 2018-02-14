from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.http.response import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
import json
import os
from rest_framework import mixins, viewsets, filters
from rest_framework.authentication import TokenAuthentication, \
    SessionAuthentication

from common.views import JsonQueryFilterBackend, SimpleQueryFilterBackend

from .models import Collection, Repository
from .serializers import CollectionSerializer, RepositorySerializer
from crashmanager.models import Tool

from .SourceCodeProvider import SourceCodeProvider


@login_required(login_url='/login/')
def index(request):
    return redirect('covmanager:collections')


@login_required(login_url='/login/')
def repositories(request):
    repositories = Repository.objects.all()
    return render(request, 'repositories/index.html', {'repositories': repositories})


@login_required(login_url='/login/')
def collections(request):
    return render(request, 'collections/index.html', {})


@login_required(login_url='/login/')
def collections_browse(request, collectionid):
    return render(request, 'collections/browse.html', {'collectionid': collectionid})


@login_required(login_url='/login/')
def collections_diff(request):
    return render(request, 'collections/browse.html', {'diff_api': True})


@login_required(login_url='/login/')
def collections_browse_api(request, collectionid, path):
    collection = get_object_or_404(Collection, pk=collectionid)

    coverage = collection.subset(path)

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


@login_required(login_url='/login/')
def collections_diff_api(request, path):

    collections = None
    coverages = []

    if "ids" in request.GET:
        ids = request.GET["ids"].split(",")
        collections = Collection.objects.filter(pk__in=ids)

    if len(collections) < 2:
        raise Http404("Need at least two collections")

    # coverage = collection.subset(path)

    # if "children" in coverage:
    #    # Viewing a directory, so we should remove detailed coverage
    #    # information before returning this data.
    #    Collection.strip(coverage)
    # else:
    #    raise Http404("NYI")

    tooltipdata = []

    for collection in collections:
        coverage = collection.subset(path)

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


@login_required(login_url='/login/')
def collections_patch(request):
    return render(request, 'collections/patch.html', {})


@login_required(login_url='/login/')
def collections_patch_api(request, collectionid, patch_revision):
    collection = get_object_or_404(Collection, pk=collectionid)

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


@login_required(login_url='/login/')
def repositories_search_api(request):
    results = []

    if "name" in request.GET:
        name = request.GET["name"]
        results = Repository.objects.filter(name__contains=name).values_list('name', flat=True)

    return HttpResponse(json.dumps({"results": list(results)}), content_type='application/json')


@login_required(login_url='/login/')
def tools_search_api(request):
    results = []

    if "name" in request.GET:
        name = request.GET["name"]
        results = Tool.objects.filter(name__contains=name).values_list('name', flat=True)

    return HttpResponse(json.dumps({"results": list(results)}), content_type='application/json')


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
