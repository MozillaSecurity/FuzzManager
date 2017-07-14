from collections import OrderedDict
from datetime import datetime, timedelta
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import SuspiciousOperation, PermissionDenied
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.db.models import F, Q
from django.db.models.aggregates import Count, Min, Max
from django.http import Http404
from django.http.response import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
import json
import operator
from rest_framework import filters, mixins, viewsets
from rest_framework.authentication import TokenAuthentication
from rest_framework.response import Response

from crashmanager.models import Tool, Client
from .models import Collection, Repository

from .models import Collection, Repository
from .serializers import InvalidArgumentException, CollectionSerializer

class CollectionViewSet(mixins.CreateModelMixin,
                        mixins.ListModelMixin,
                        mixins.RetrieveModelMixin,
                        viewsets.GenericViewSet):
    """
    API endpoint that allows adding/viewing Collections
    """
    authentication_classes = (TokenAuthentication,)
    queryset = Collection.objects.all()
    serializer_class = CollectionSerializer
