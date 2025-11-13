# This is code for Mozilla's 2FA using OID. If you have your own OID provider,
# you can probably use similar code to get 2FA for your FuzzManager instance.

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

            if request.user.has_perm(f"crashmanager.view_{app}"):
                if request.user.has_perm(f"crashmanager.{app}_all"):
                    return True
                view_name = type(view).__name__
                if app == "crashmanager":
                    if view_name == "SignaturesDownloadView" and request.user.has_perm(
                        f"{app}.{app}_download_signatures"
                    ):
                        return True
                    if (
                        view_name == "CrashEntryViewSet"
                        and request.method == "POST"
                        and not view.detail
                        and request.user.has_perm(f"{app}.{app}_report_crashes")
                    ):
                        return True
                elif app == "taskmanager":
                    if (
                        view_name == "TaskViewSet"
                        and request.method == "POST"
                        and view.action == "update_status"
                        and not view.detail
                        and request.user.has_perm(f"crashmanager.{app}_report_status")
                    ):
                        return True
                elif app == "ec2spotmanager":
                    if (
                        view_name == "MachineStatusViewSet"
                        and request.method == "POST"
                        and request.user.has_perm(f"crashmanager.{app}_report_status")
                    ):
                        return True
                elif app == "covmanager":
                    if (
                        view_name == "CollectionViewSet"
                        and request.method == "POST"
                        and not view.detail
                        and request.user.has_perm(
                            f"crashmanager.{app}_submit_collection"
                        )
                    ):
                        return True
                    if (
                        view_name == "ReportConfigurationViewSet"
                        and request.method == "GET"
                        and request.user.has_perm(
                            f"crashmanager.{app}_view_report_configurations"
                        )
                    ):
                        return True
        return False
