from django.apps import apps
from django.conf import settings
from django.conf.urls import include
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth.views import LogoutView
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import re_path
from notifications import views as notifications_views

from .views import index, login

admin.autodiscover()


urlpatterns = [
    re_path(r"^$", index, name="index"),
    # re_path(r'^admin/', include(admin.site.urls)),
    re_path(r"^login/$", login, name="login"),
    re_path(r"^logout/$", LogoutView.as_view(), name="logout"),
    re_path(r"^covmanager/", include("covmanager.urls")),
    re_path(r"^crashmanager/", include("crashmanager.urls")),
    re_path(r"^taskmanager/", include("taskmanager.urls")),
    re_path(
        "inbox/notifications/",
        include(
            (
                [
                    re_path(
                        r"^unread/$",
                        notifications_views.UnreadNotificationsList.as_view(),
                        name="unread",
                    ),
                    re_path(
                        r"^mark-all-as-read/$",
                        notifications_views.mark_all_as_read,
                        name="mark_all_as_read",
                    ),
                    re_path(
                        r"^api/unread_count/$",
                        notifications_views.live_unread_notification_count,
                        name="live_unread_notification_count",
                    ),
                ],
                "notifications",
            )
        ),
    ),
]

if settings.USE_OIDC:
    urlpatterns.append(re_path(r"^oidc/", include("mozilla_django_oidc.urls")))

if apps.is_installed("ec2spotmanager"):
    urlpatterns.append(re_path(r"^ec2spotmanager/", include("ec2spotmanager.urls")))

urlpatterns += staticfiles_urlpatterns()
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
