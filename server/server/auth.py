# This is code for Mozilla's 2FA using OID. If you have your own OID provider,
# you can probably use similar code to get 2FA for your WebCompatManager instance.

import unicodedata

from django.conf import settings
from rest_framework import permissions

if getattr(settings, "USE_OIDC", False):
    from mozilla_django_oidc.auth import OIDCAuthenticationBackend

    def generate_username(email):
        # Using Python 3 and Django 1.11, usernames can contain alphanumeric
        # (ascii and unicode), _, @, +, . and - characters. So we normalize
        # it and slice at 150 characters.
        return unicodedata.normalize("NFKC", email)[:150]

    class FMOIDCAB(OIDCAuthenticationBackend):
        def verify_claims(self, claims):
            verified = super().verify_claims(claims)

            if not verified:
                return False

            email = claims.get("email", None)
            return email in settings.OID_ALLOWED_USERS


class CheckAppPermission(permissions.BasePermission):
    """
    Check that user has permission to view this app, whether via REST or web UI.
    """

    def has_permission(self, request, view):
        if request.user and request.user.is_authenticated:
            app = view.__module__.split(".", 1)[0]
            view_name = request.resolver_match.url_name
            print(f"app={app} view_name={view_name}")

            if request.user.has_perm(f"reportmanager.{app}_visible"):
                if request.user.has_perm(f"reportmanager.{app}_read"):
                    if request.method in {"GET", "HEAD"}:
                        return True
                    if request.method == "POST" and view_name in {
                        "bucketwatchnew",
                        "bucketwatchdel",
                        "usersettings",
                    }:
                        return True
                    if request.method == "PATCH" and view_name in {
                        "inbox-mark-all-as-read",
                        "inbox-mark-as-read",
                    }:
                        return True

                if request.user.has_perm(
                    f"reportmanager.{app}_write"
                ) and request.method in {
                    "DELETE",
                    "PATCH",
                    "POST",
                    "PUT",
                }:
                    return True
        return False
