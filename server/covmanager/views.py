from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.http.response import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
import json
from rest_framework import mixins, viewsets
from rest_framework.authentication import TokenAuthentication, \
    SessionAuthentication

from common.views import JsonQueryFilterBackend, SimpleQueryFilterBackend, paginate_requested_list, renderError

from .models import Collection, Repository
from .serializers import CollectionSerializer, RepositorySerializer

@login_required(login_url='/login/')
def index(request):
    return redirect('covmanager:collections')

@login_required(login_url='/login/')
def repositories(request):
    repositories = Repository.objects.all()
    return render(request, 'repositories/index.html', { 'repositories' : repositories })

@login_required(login_url='/login/')
def collections(request):
    return render(request, 'collections/index.html', {})

@login_required(login_url='/login/')
def collections_browse(request, collectionid):
    return render(request, 'collections/browse.html', { 'collectionid' : collectionid })

@login_required(login_url='/login/')
def collections_diff(request):
    # TODO: Selecting IDs here should be based on a search query
    if "ids" in request.GET:
        ids = request.GET["ids"].split(",")
    else:
        raise Http404("No ids specified.")
    return render(request, 'collections/browse.html', { 'ids': ids, 'diff_api': True })

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

    data = { "path" : path, "coverage" : coverage }
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
        for k in start_coverage["children"][child]:
            x = start_coverage["children"][child][k]
            # TODO: This assumes child is in end_coverage, which can fail
            if type(x) == int:
                add["delta_" + k] = end_coverage["children"][child][k] - x
            elif type(x) == float:
                add["delta_" + k] = round(end_coverage["children"][child][k] - x, 4)
        start_coverage["children"][child].update(add)

    data = { "path" : path, "coverage" : start_coverage, "ttdata" : tooltipdata }
    return HttpResponse(json.dumps(data), content_type='application/json')

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
    filter_backends = [JsonQueryFilterBackend, SimpleQueryFilterBackend]

class RepositoryViewSet(mixins.CreateModelMixin,
                        mixins.ListModelMixin,
                        mixins.RetrieveModelMixin,
                        viewsets.GenericViewSet):
    """
    API endpoint that allows viewing Repositories
    """
    authentication_classes = (TokenAuthentication,)
    queryset = Repository.objects.all()
    serializer_class = RepositorySerializer
    filter_backends = [JsonQueryFilterBackend]
