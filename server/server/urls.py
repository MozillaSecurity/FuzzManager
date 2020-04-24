from django.conf.urls import include, url
from django.contrib import admin
from django.contrib.auth.views import LogoutView
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
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
]
urlpatterns += staticfiles_urlpatterns()
