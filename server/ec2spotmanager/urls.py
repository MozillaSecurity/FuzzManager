from django.conf.urls import patterns, url
from ec2spotmanager import views

urlpatterns = patterns('',
    url(r'^logout/$', views.logout_view, name='logout'),
    url(r'^$', views.index, name='index'),
    url(r'^pools/$', views.pools, name='pools'),
    url(r'^pools/(?P<poolid>\d+)/$', views.viewPool, name='poolview'),
    url(r'^pools/(?P<poolid>\d+)/delete/$', views.deletePool, name='pooldel'),
    url(r'^pools/messages/(?P<msgid>\d+)/delete/$', views.deletePoolMsg, name='poolmsgdel'),
    url(r'^configurations/(?P<configid>\d+)/$', views.viewConfig, name='configview'),
    url(r'^configurations/(?P<configid>\d+)/$', views.deleteConfig, name='configdel'),
)