from django.conf.urls import url, include
from rest_framework import routers
from . import views


router = routers.DefaultRouter()
router.register(r'configurations', views.PoolConfigurationViewSet, basename='configurations')


app_name = 'ec2spotmanager'
urlpatterns = [
    url(r'^rest/api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    url(r'^rest/report/$', views.MachineStatusViewSet.as_view()),
    url(r'^rest/pool/(?P<poolid>\d+)/cycle/$', views.PoolCycleView.as_view()),
    url(r'^rest/pool/(?P<poolid>\d+)/enable/$', views.PoolEnableView.as_view()),
    url(r'^rest/pool/(?P<poolid>\d+)/disable/$', views.PoolDisableView.as_view()),
    url(r'^$', views.index, name='index'),
    url(r'^providers/messages/(?P<msgid>\d+)/delete/$', views.deleteProviderMsg, name='providermsgdel'),
    url(r'^pools/$', views.pools, name='pools'),
    url(r'^pools/create/$', views.createPool, name='poolcreate'),
    url(r'^pools/(?P<poolid>\d+)/$', views.viewPool, name='poolview'),
    url(r'^pools/(?P<poolid>\d+)/prices/$', views.viewPoolPrices, name='poolprices'),
    url(r'^pools/(?P<poolid>\d+)/delete/$', views.deletePool, name='pooldel'),
    url(r'^pools/(?P<poolid>\d+)/enable/$', views.enablePool, name='poolenable'),
    url(r'^pools/(?P<poolid>\d+)/disable/$', views.disablePool, name='pooldisable'),
    url(r'^pools/(?P<poolid>\d+)/cycle/$', views.forceCyclePool, name='poolcycle'),
    url(r'^pools/messages/(?P<msgid>\d+)/delete/$', views.deletePoolMsg, name='poolmsgdel'),
    url(r'^pools/messages/(?P<msgid>\d+)/delete/from_pool$', views.deletePoolMsg, name='poolmsgdel_from_pool',
        kwargs={'from_pool': '1'}),
    url(r'^configurations/$', views.viewConfigs, name='configs'),
    url(r'^configurations/create/$', views.createConfig, name='configcreate'),
    url(r'^configurations/(?P<configid>\d+)/$', views.viewConfig, name='configview'),
    url(r'^configurations/(?P<configid>\d+)/edit/$', views.editConfig, name='configedit'),
    url(r'^configurations/(?P<configid>\d+)/delete/$', views.deleteConfig, name='configdel'),
    url(r'^configurations/(?P<configid>\d+)/cycle/$', views.forceCyclePoolsByConfig, name='configcycle'),
    url(r'^pools/(?P<poolid>\d+)/chart_json_detailed/$', views.UptimeChartViewDetailed.as_view(),
        name='line_chart_json_detailed'),
    url(r'^pools/(?P<poolid>\d+)/chart_json_accumulated/$', views.UptimeChartViewAccumulated.as_view(),
        name='line_chart_json_accumulated'),

    url(r'^rest/', include(router.urls)),
]
