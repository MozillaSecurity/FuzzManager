from django.conf.urls import include
from django.urls import re_path
from rest_framework import routers

from . import views

router = routers.DefaultRouter()
router.register(
    r"configurations", views.PoolConfigurationViewSet, basename="configurations"
)


app_name = "ec2spotmanager"
urlpatterns = [
    re_path(
        r"^rest/api-auth/", include("rest_framework.urls", namespace="rest_framework")
    ),
    re_path(r"^rest/report/$", views.MachineStatusViewSet.as_view()),
    re_path(r"^rest/pool/(?P<poolid>\d+)/cycle/$", views.PoolCycleView.as_view()),
    re_path(r"^rest/pool/(?P<poolid>\d+)/enable/$", views.PoolEnableView.as_view()),
    re_path(r"^rest/pool/(?P<poolid>\d+)/disable/$", views.PoolDisableView.as_view()),
    re_path(r"^$", views.index, name="index"),
    re_path(
        r"^providers/messages/(?P<msgid>\d+)/delete/$",
        views.deleteProviderMsg,
        name="providermsgdel",
    ),
    re_path(r"^pools/$", views.pools, name="pools"),
    re_path(r"^pools/create/$", views.createPool, name="poolcreate"),
    re_path(r"^pools/(?P<poolid>\d+)/$", views.viewPool, name="poolview"),
    re_path(
        r"^pools/(?P<poolid>\d+)/prices/$", views.viewPoolPrices, name="poolprices"
    ),
    re_path(r"^pools/(?P<poolid>\d+)/delete/$", views.deletePool, name="pooldel"),
    re_path(r"^pools/(?P<poolid>\d+)/enable/$", views.enablePool, name="poolenable"),
    re_path(r"^pools/(?P<poolid>\d+)/disable/$", views.disablePool, name="pooldisable"),
    re_path(r"^pools/(?P<poolid>\d+)/cycle/$", views.forceCyclePool, name="poolcycle"),
    re_path(
        r"^pools/messages/(?P<msgid>\d+)/delete/$",
        views.deletePoolMsg,
        name="poolmsgdel",
    ),
    re_path(
        r"^pools/messages/(?P<msgid>\d+)/delete/from_pool$",
        views.deletePoolMsg,
        name="poolmsgdel_from_pool",
        kwargs={"from_pool": "1"},
    ),
    re_path(r"^configurations/$", views.viewConfigs, name="configs"),
    re_path(r"^configurations/create/$", views.createConfig, name="configcreate"),
    re_path(
        r"^configurations/(?P<configid>\d+)/$", views.viewConfig, name="configview"
    ),
    re_path(
        r"^configurations/(?P<configid>\d+)/edit/$", views.editConfig, name="configedit"
    ),
    re_path(
        r"^configurations/(?P<configid>\d+)/delete/$",
        views.deleteConfig,
        name="configdel",
    ),
    re_path(
        r"^configurations/(?P<configid>\d+)/cycle/$",
        views.forceCyclePoolsByConfig,
        name="configcycle",
    ),
    re_path(
        r"^pools/(?P<poolid>\d+)/chart_json_detailed/$",
        views.UptimeChartViewDetailed.as_view(),
        name="line_chart_json_detailed",
    ),
    re_path(
        r"^pools/(?P<poolid>\d+)/chart_json_accumulated/$",
        views.UptimeChartViewAccumulated.as_view(),
        name="line_chart_json_accumulated",
    ),
    re_path(r"^rest/", include(router.urls)),
]
