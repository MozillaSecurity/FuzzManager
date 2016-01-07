from django.conf.urls import patterns, url, include
from rest_framework import routers

from ec2spotmanager import views


router = routers.DefaultRouter()
router.register(r'report', views.MachineStatusViewSet)

urlpatterns = patterns('',
    url(r'^rest/api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    url(r'^rest/', include(router.urls)),
    url(r'^logout/$', views.logout_view, name='logout'),
    url(r'^$', views.index, name='index'),
    url(r'^pools/$', views.pools, name='pools'),
    url(r'^pools/create/$', views.createPool, name='poolcreate'),
    url(r'^pools/(?P<poolid>\d+)/$', views.viewPool, name='poolview'),
    url(r'^pools/(?P<poolid>\d+)/prices/$', views.viewPoolPrices, name='poolprices'),
    url(r'^pools/(?P<poolid>\d+)/delete/$', views.deletePool, name='pooldel'),
    url(r'^pools/(?P<poolid>\d+)/enable/$', views.enablePool, name='poolenable'),
    url(r'^pools/(?P<poolid>\d+)/disable/$', views.disablePool, name='pooldisable'),
    url(r'^pools/(?P<poolid>\d+)/cycle/$', views.forceCyclePool, name='poolcycle'),
    url(r'^pools/messages/(?P<msgid>\d+)/delete/$', views.deletePoolMsg, name='poolmsgdel'),
    url(r'^configurations/$', views.viewConfigs, name='configs'),
    url(r'^configurations/create/$', views.createConfig, name='configcreate'),
    url(r'^configurations/(?P<configid>\d+)/$', views.viewConfig, name='configview'),
    url(r'^configurations/(?P<configid>\d+)/edit/$', views.editConfig, name='configedit'),
    url(r'^configurations/(?P<configid>\d+)/delete/$', views.deleteConfig, name='configdel'),
    url(r'^configurations/(?P<configid>\d+)/cycle/$', views.forceCyclePoolsByConfig, name='configcycle'),
    url(r'^pools/(?P<poolid>\d+)/chart_json_detailed/$', views.UptimeChartViewDetailed.as_view(), name='line_chart_json_detailed'),
    url(r'^pools/(?P<poolid>\d+)/chart_json_accumulated/$', views.UptimeChartViewAccumulated.as_view(), name='line_chart_json_accumulated'),
)