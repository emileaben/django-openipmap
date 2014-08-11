from django.conf.urls import patterns, url, include
from rest_framework import routers
#from rest_framework_nested import routers
from routergeoloc import views

router = routers.SimpleRouter()
router.register(r'domain_regex_rules', views.DomainRegexRuleViewSet)
router.register(r'my_domain_regex_rules', views.MyDomainRegexRuleViewSet)
router.register(r'ip_rules', views.IPRuleViewSet)
router.register(r'my_ip_rules', views.MyIPRuleViewSet)
router.register(r'my_hostname_rules', views.MyHostnameRuleViewSet)
router.register(r'hostname_rules', views.HostnameRuleViewSet)
#domains_router = routers.NestedSimpleRouter(router, r'domains', lookup='domain')
#domains_router.register(r'nameservers', NameserverViewSet)
#router = routers.DefaultRouter()
#router = routers.SimpleRouter()
#router.register(r'domaincontribution', views.DomainContributionViewSet)
#router.register(r'domain_regex_rule', views.DomainRegexRuleViewSet)
#dom_router = routers.NestedSimpleRouter(router, r'domaincontribution', lookup='domaincontribution')
#dom_router.register(r'regexrule', views.DomainRegexRuleViewSet)

urlpatterns = patterns('',
    url(r'^$', views.index, name='index'),
    url(r'^api/', include(router.urls)),
    url(r'^msmfetch.json$', views.msmfetch, name='msmfetch'),
    url(r'^ipmeta.json$', views.ipmeta, name='ipmeta'),
    url(r'^ipmap$', views.ipmap, name='ipmap'),
    url(r'^tracemap-test', views.tracemap, {'is_test': True}, name='tracemap'),
    url(r'^tracemap', views.tracemap, name='tracemap'),
    url(r'^analyse-domain', views.analyse_domain, name='analyse_domain'),
    url(r'^bulk-upload/', views.bulk_upload, name='bulk_upload'),
)
