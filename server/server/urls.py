from django.conf import settings
from django.conf.urls import include, url
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth.views import LogoutView
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from notifications import views as notifications_views
from .views import index, login


admin.autodiscover()


urlpatterns = [
    #url(r'^oidc/', include('mozilla_django_oidc.urls')),  # uncomment this for mozilla_django_oidc
    url(r'^$', index, name='index'),
    # url(r'^admin/', include(admin.site.urls)),
    url(r'^login/$', login, name="login"),
    url(r'^logout/$', LogoutView.as_view(), name="logout"),
    url(r'^covmanager/', include('covmanager.urls')),
    url(r'^crashmanager/', include('crashmanager.urls')),
    url(r'^taskmanager/', include('taskmanager.urls')),
    url(r'^ec2spotmanager/', include('ec2spotmanager.urls')),
    url('inbox/notifications/', include(([
        url(r'^unread/$', notifications_views.UnreadNotificationsList.as_view(), name='unread'),
        url(r'^mark-all-as-read/$', notifications_views.mark_all_as_read, name='mark_all_as_read'),
        url(r'^api/unread_count/$', notifications_views.live_unread_notification_count,
            name='live_unread_notification_count'),
    ], 'notifications'))),
]
urlpatterns += staticfiles_urlpatterns()
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
