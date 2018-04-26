"""
Based on snippet from https://stackoverflow.com/a/46976284
Docstring and original idea from https://stackoverflow.com/a/2164224
"""
import re

from django.conf import settings
from django.contrib.auth.decorators import login_required


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
    def __init__(self):
        self.exceptions = re.compile("(" + "|".join(settings.LOGIN_REQUIRED_URLS_EXCEPTIONS) + ")")

    def process_view(self, request, view_func, view_args, view_kwargs):
        # No need to process URLs if user already logged in
        if request.user.is_authenticated:
            return None

        # An exception match should immediately return None
        if self.exceptions.match(request.path):
            return None

        # Non-matching requests are returned wrapped with the login_required decorator
        return login_required(view_func)(request, *view_args, **view_kwargs)
