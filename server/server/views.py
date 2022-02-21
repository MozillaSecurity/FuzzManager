from __future__ import annotations

from django.shortcuts import redirect
from django.contrib.auth.views import LoginView
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage, Page
from django.db.models import Model
from django.db.models import Q
from django.db.models.query import QuerySet
from django.http.request import HttpRequest
from django.http.response import HttpResponse
from django.http.response import HttpResponsePermanentRedirect
from django.http.response import HttpResponseRedirect
from django.shortcuts import render
from django.urls import resolve, reverse
import collections
import functools
import json
from rest_framework import filters
from rest_framework.request import Request
from rest_framework.views import APIView
import six
from typing import Any
from typing import TypeVar
from typing import cast

from crashmanager.models import User
from server.covmanager.models import Collection

MT = TypeVar("MT", bound=Model)


def index(request: HttpRequest) -> HttpResponseRedirect | HttpResponsePermanentRedirect:
    user = User.get_or_create_restricted(request.user)[0]
    # return crashmanager, covmanager, or ec2spotmanager, as allowed, in that order.
    # if no permission to view any apps, then use crashmanager and let that fail
    if not user.user.has_perm('crashmanager.view_crashmanager'):
        if user.user.has_perm('crashmanager.view_covmanager'):
            return redirect('covmanager:index')
        elif user.user.has_perm('crashmanager.view_ec2spotmanager'):
            return redirect('ec2spotmanager:index')
    return redirect('crashmanager:index')


def login(request: HttpRequest):
    if settings.USE_OIDC:
        auth_view = resolve(reverse('oidc_authentication_init')).func
        return auth_view(request)
    return LoginView.as_view()(request)


def deny_restricted_users(wrapped: collections.abc.Callable[..., Any]) -> collections.abc.Callable[..., Any]:
    @functools.wraps(wrapped)
    def decorator(request: HttpRequest, *args: Any, **kwargs: Any) -> Any:
        user = User.get_or_create_restricted(request.user)[0]
        if user.restricted:
            raise PermissionDenied({"message": "You don't have permission to access this view."})
        return wrapped(request, *args, **kwargs)
    return decorator


def renderError(request: HttpRequest, err: str) -> HttpResponse:
    return render(request, 'error.html', {'error_message': err})  # noqa


def paginate_requested_list(request: HttpRequest, entries: QuerySet[Model]) -> Page:
    """
    This method generically paginates a given QuerySet and returns a list
    suitable for passing to a template. The set is paginated by request
    parameters 'page' and 'page_size'.
    """
    page_size = request.GET.get('page_size')
    if not page_size:
        assert page_size is not None
        page_size_int = int(page_size)
        page_size_int = 100
    paginator = Paginator(entries, page_size_int)
    page = request.GET.get('page')

    try:
        assert page is not None
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


def json_to_query(json_str: str):
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
        obj = json.loads(json_str, object_pairs_hook=collections.OrderedDict)  # noqa
    except ValueError as e:
        raise RuntimeError("Invalid JSON: %s" % e)

    def get_query_obj(obj: six.text_type | list[str] | int | dict[str, str] | None, key: str | None = None) -> Q:

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
        objkeys = list(obj)
        objkeys.remove("op")

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


class JsonQueryFilterBackend(filters.BaseFilterBackend):
    """
    Accepts filtering with a query parameter which builds a Django query from JSON (see json_to_query)
    """
    def filter_queryset(self, request: Request, queryset: QuerySet[MT], view: APIView) -> QuerySet[MT]:
        """
        Return a filtered queryset.
        """
        querystr = request.query_params.get('query', None)
        if querystr is not None:
            try:
                _, queryobj = json_to_query(querystr)
            except RuntimeError as e:
                raise InvalidArgumentException("error in query: %s" % e)  # noqa
            queryset = queryset.filter(queryobj)
        return queryset


class SimpleQueryFilterBackend(filters.BaseFilterBackend):
    """
    Accepts filtering with a query parameter which builds a Django query using simple "contains" searches
    """
    def filter_queryset(self, request: Request, queryset: QuerySet[MT], view: APIView) -> QuerySet[MT]:
        """
        Return a filtered queryset.
        """
        # Return early on empty queryset
        if not queryset:
            return queryset

        querystr = request.query_params.get('squery', None)
        if querystr is not None:
            queryobj = None
            for field in cast(Collection, queryset[0]).simple_query_fields:
                kwargs = {"%s__contains" % field: querystr}
                if queryobj is None:
                    queryobj = Q(**kwargs)
                else:
                    queryobj.add(Q(**kwargs), Q.OR)

            queryset = queryset.filter(queryobj).distinct()
        return queryset
