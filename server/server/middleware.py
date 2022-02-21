from __future__ import annotations

import re
import traceback
from types import TracebackType
from typing import Any
from typing import Callable

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.http.request import HttpRequest
from django.http.response import HttpResponse
from rest_framework.request import Request
from rest_framework.views import APIView

from crashmanager.models import User
from .auth import CheckAppPermission


class ExceptionLoggingMiddleware(object):
    """
    This tiny middleware module allows us to see exceptions on stderr
    when running a Django instance with runserver.py
    """
    def __init__(self, get_response: Callable[..., Any]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest):
        return self.get_response(request)

    def process_exception(self, request: HttpRequest, exception: tuple[
            type[BaseException] | None,
            type[BaseException] | None,
            TracebackType | None
        ]) -> None:
        print(traceback.format_exc())
        return None


class RequireLoginMiddleware(object):
    """
    Middleware component that wraps the login_required decorator around
    matching URL patterns. To use, add the class to MIDDLEWARE_CLASSES and
    define LOGIN_REQUIRED_URLS_EXCEPTIONS in your settings.py. For example:
    ------
    LOGIN_REQUIRED_URLS_EXCEPTIONS = (
        r'/topsecret/login(.*)$',
        r'/topsecret/logout(.*)$',
    )
    ------
    LOGIN_REQUIRED_URLS_EXCEPTIONS is, conversely, where you explicitly
    define any exceptions (like login and logout URLs).
    """
    # Based on snippet from https://stackoverflow.com/a/46976284
    # Docstring and original idea from https://stackoverflow.com/a/2164224
    def __init__(self, get_response: Callable[..., Any]) -> None:
        self.get_response = get_response
        self.exceptions = re.compile("(" + "|".join(settings.LOGIN_REQUIRED_URLS_EXCEPTIONS) + ")")

    def __call__(self, request: HttpRequest):
        return self.get_response(request)

    def process_view(self, request: HttpRequest, view_func: Callable[..., Any], view_args: Any, view_kwargs: Any) -> Any:
        # No need to process URLs if user already logged in
        if request.user.is_authenticated:
            return None

        # An exception match should immediately return None
        if self.exceptions.match(request.path):
            return None

        # Non-matching requests are returned wrapped with the login_required decorator
        return login_required(view_func)(request, *view_args, **view_kwargs)


class CheckAppPermissionsMiddleware(object):

    def __init__(self, get_response: Callable[..., Any]) -> None:
        self.get_response = get_response
        self.exceptions = re.compile("(" + "|".join(settings.LOGIN_REQUIRED_URLS_EXCEPTIONS) + ")")

    def __call__(self, request: HttpRequest):
        return self.get_response(request)

    def process_view(self, request: Request, view_func: APIView, view_args: Any, view_kwargs: Any) -> HttpResponseForbidden | None:
        # Get the app name
        app = view_func.__module__.split('.', 1)[0]

        if app in {'notifications', 'server'}:
            return None

        # If no login is required for this path, we can't check permissions
        if self.exceptions.match(request.path):
            return None

        User.get_or_create_restricted(request.user)  # create a CrashManager user if needed to apply defaults

        if not CheckAppPermission().has_permission(request, view_func):
            return HttpResponseForbidden()

        return None
