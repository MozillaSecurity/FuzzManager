from django.conf.urls import patterns, include, url
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

admin.autodiscover()

urlpatterns = patterns('',
    url(r'^$', 'crashmanager.views.index', name='index'),
    # url(r'^admin/', include(admin.site.urls)),
    url(r'^login/$', 'django.contrib.auth.views.login'),
    url(r'^crashmanager/', include('crashmanager.urls', namespace="crashmanager", app_name='crashmanager')),
    url(r'^ec2spotmanager/', include('ec2spotmanager.urls', namespace="ec2spotmanager", app_name='ec2spotmanager')),
)

urlpatterns += staticfiles_urlpatterns()
