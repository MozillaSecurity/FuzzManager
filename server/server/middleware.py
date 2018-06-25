from __future__ import print_function
import re
import traceback

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden

from crashmanager.models import User
from .auth import CheckAppPermission


class ExceptionLoggingMiddleware(object):
    """
    This tiny middleware module allows us to see exceptions on stderr
    when running a Django instance with runserver.py
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
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
    def __init__(self, get_response):
        self.get_response = get_response
        self.exceptions = re.compile("(" + "|".join(settings.LOGIN_REQUIRED_URLS_EXCEPTIONS) + ")")

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        # No need to process URLs if user already logged in
        if request.user.is_authenticated:
            return None

        # An exception match should immediately return None
        if self.exceptions.match(request.path):
            return None

        # Non-matching requests are returned wrapped with the login_required decorator
        return login_required(view_func)(request, *view_args, **view_kwargs)


class CheckAppPermissionsMiddleware(object):

    def __init__(self, get_response):
        self.get_response = get_response
        self.exceptions = re.compile("(" + "|".join(settings.LOGIN_REQUIRED_URLS_EXCEPTIONS) + ")")

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        # Get the app name
        app = view_func.__module__.split('.', 1)[0]

        if app == 'server':
            return None

        # If no login is required for this path, we can't check permissions
        if self.exceptions.match(request.path):
            return None

        User.get_or_create_restricted(request.user)  # create a CrashManager user if needed to apply defaults

        if not CheckAppPermission().has_permission(request, view_func):
            return HttpResponseForbidden()

        return None
