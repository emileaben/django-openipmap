# Create your views here.
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.template import RequestContext
from django.shortcuts import render_to_response
from openipmap.models import *
from openipmap.utils import *
from openipmap.forms import ContributionUploadForm
from openipmap.serializers import *
from openipmap.permissions import *
from rest_framework import viewsets
from rest_framework import permissions
import urllib
import time
import ipaddress
import json
import sys

#from routergeoloc.profile import *

### API
## as modelviewset
class DomainRegexRuleViewSet(viewsets.ModelViewSet):
    queryset=DomainRegexRule.objects.all()
    serializer_class = DomainRegexRuleSerializer

class MyDomainRegexRuleViewSet(viewsets.ModelViewSet):
    queryset=DomainRegexRule.objects.all()
    serializer_class = MyDomainRegexRuleSerializer
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,
                          IsOwnerOrReadOnly,)
    def get_queryset(self):
        user = self.request.user
        return DomainRegexRule.objects.filter(user=user)
    def pre_save(self,obj):
        obj.user = self.request.user

class IPRuleViewSet(viewsets.ModelViewSet):
    queryset=IPRule.objects.all()
    serializer_class = IPRuleSerializer

class MyIPRuleViewSet(viewsets.ModelViewSet):
    queryset=IPRule.objects.all()
    serializer_class = MyIPRuleSerializer
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,
                          IsOwnerOrReadOnly,)
    def get_queryset(self):
        user = self.request.user
        return IPRule.objects.filter(user=user)
    def pre_save(self,obj):
        obj.user = self.request.user

class HostnameRuleViewSet(viewsets.ModelViewSet):
    queryset=HostnameRule.objects.all()
    serializer_class = HostnameRuleSerializer

class MyHostnameRuleViewSet(viewsets.ModelViewSet):
    queryset=HostnameRule.objects.all()
    serializer_class = MyHostnameRuleSerializer
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,
                          IsOwnerOrReadOnly,)
    def get_queryset(self):
        user = self.request.user
        return HostnameRule.objects.filter(user=user)
    def pre_save(self,obj):
        obj.user = self.request.user

    ## override POST behaviour
    def create(self,req):
        result = super(MyHostnameRuleViewSet, self).create(req)
        ## return geoloc // todo: cache it/store it in the db on creation?
        ##result.data['aap'] = "yeah yeah"
        return result

'''
class DomainContributionViewSet(viewsets.ModelViewSet):
    queryset = DomainContribution.objects.all()
    serializer_class = DomainContributionSerializer

## this ain't working
class DomainRegexRuleViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = DomainRegexRule.objects.all()
    serializer_class = DomainRegexRuleSerializer
'''
@login_required
def post_domain_regex_rule(req):
    user=req.user
    if request.method != 'POST':
        return HttpResponse("not a post")
    try:
        rule_json = HttpRequest.POST['rule']
        rule_vals = json.loads( rule_json )
        dom_contrib,is_created = DomainContribution.objects.get_or_create( user=user, domain=rule_vals['domain'] )
        if is_created:
            dom_contrib.save()
        rule = DomainRegexRule()
        rule.regex = rule_vals['regex']
        rule.result = rule_vals['result']
        rule.confidence = rule_vals['confidence']
        rule.contribution = dom_contrib
        rule.save()
    except:
        return HttpResponse("'rule' param in the post not json")
    return HttpResponse("Object created")

@login_required
def index(req):
    return render_to_response(
        'idx.html',
        {}
    )

def msmfetch(request):
    try: msm_id = int(request.GET.get('msm_id'))
    except:
        return HttpResponse("no msm_id")

    ## get msm_info   
    ##### not used yet, but msm_info could be used to work on start/stop/interval/probes etc.
    #msm_info_url = "https://atlas.ripe.net/api/v1/measurement/%s/?format=json" % ( msm_id )
    #try:
    #    info_fh = urllib.urlopen( msm_info_url )
    #except Exception as err:
    #    return HttpResponse(status=err[1])
    #info_json = info_fh.read()
    #msm_info = json.loads( info_json )
    ### here

    limit=4
    try: limit = int(request.GET.get('limit'))
    except: pass

    stop=int(time.time())
    try: stop = int(request.GET.get('stop'))
    except: pass

    interval=3600
    try: interval = int(request.GET.get('interval'))
    except: pass

    probes=''
    try: 
      probes = request.GET.get('probes')
    except: pass

    

    start = stop - interval
    #msm_url = "https://atlas.ripe.net/api/v1/measurement/%d/result/?start=%d&stop=%d&format=txt&limit=%d" % ( int(msm_id), start_t, end_t, limit )
    ### limit doesn't work?
    ####TODO use latest? https://atlas.ripe.net/api/v1/measurement-latest/1636208/
    #OLD# msm_url = "https://atlas.ripe.net/api/v1/measurement/%d/result/?start=%d&stop=%d&limit=%d" % ( msm_id, start, stop, limit )
    version_count = 1
    msm_url = "https://atlas.ripe.net/api/v1/measurement-latest/%s/?versions=%s" % ( msm_id, version_count )
    if probes:
        msm_url += "&probes=%s" % ( probes )
    try:
        url_fh = urllib.urlopen( msm_url )
    except Exception as err:
        # err[1] will have the HTTP status code
        if isinstance( err[1], int):
           return HttpResponse(status=err[1])
        else:
           return HttpResponse(status=500)
    msm_json = url_fh.read()
    data = json.loads(msm_json)
    d = {
        'ips': {}, # contains ip->traceroute map
        'trs': {}, # contains traceroute->ip map
        'prb': {}, # contains info on probes encountered
        'dst_addrs': {}, # contains trace destinations, keyed on trace_id
        'dst_names': {}, # contains trace dst names, keyed on trace_id
        'err': []
    } # data struct
    d['msm_url'] = msm_url
    for key,msm_list in data.items():
        try:
            msm = msm_list[0]
            ts = msm['timestamp']
            prb_id = int(key)
            if not prb_id in d['prb']:
                try:
                    p = Probe.objects.get(id=prb_id)
                    d['prb'][prb_id] = {
                        'lat': p.lat,
                        'lon': p.lon,
                    }
                except:
                    pass
            msm_id = msm['msm_id']
            tr_id = "%s|%s|%s" % (msm_id,prb_id,ts) ## may be able to encode better?
            if 'dst_addr' in msm:
                d['dst_addrs'][tr_id] = msm['dst_addr']
            if 'dst_name' in msm:
                d['dst_names'][tr_id] = msm['dst_name']
            for msm_res in msm['result']:
                hop_nr = int(msm_res['hop'])
                for hop_res in msm_res['result']:
                    if 'from' in hop_res:
                        ip = hop_res['from']
                        rtt = None
                        try:
                            rtt = float(hop_res['rtt'])
                            rtt = "%0.1f" % rtt
                        except: pass

                        ## fill 'ips'
                        if not ip in d['ips']:
                            d['ips'][ip] = {'traces':{}}
                        if not tr_id in d['ips'][ip]['traces']:
                            d['ips'][ip]['traces'][tr_id] = {'hop': hop_nr, 'rtt': rtt}
                        else:
                            if d['ips'][ip]['traces'][tr_id]['hop'] > hop_nr:
                                d['ips'][ip]['traces'][tr_id]['hop'] = hop_nr
                            if d['ips'][ip]['traces'][tr_id]['rtt'] > rtt:
                                d['ips'][ip]['traces'][tr_id]['rtt'] = rtt
                        ## fill 'trs'
                        ## maybe make this just raw trace results, and have them javascript-processed client-side?
                        if not tr_id in d['trs']:
                            d['trs'][tr_id] = {};
                        if not hop_nr in d['trs'][tr_id]:
                            d['trs'][tr_id][hop_nr] = {}
                        if not ip in d['trs'][tr_id][hop_nr]:
                            d['trs'][tr_id][hop_nr][ip] = []
                        d['trs'][tr_id][hop_nr][ip].append( rtt );
                        #    d['trs'][tr_id] = {'trace': [] }
                        #d['trs'][tr_id]['trace'].append({'rtt': rtt, 'hop': hop_nr, 'ip': ip})
        except:
            import traceback
            exc=sys.exc_info()
            d['err'].append( traceback.format_exc() );
    return HttpResponse(
        json.dumps( d, indent=2 ),
        content_type="application/json"
    )

def iprtt(request):
    '''
     accepts tuples of q=<ip>|<lat>|<lon>|<min_rtt>
     returns same as ipmeta, but now with geoconstraints applied
    '''
    ## TODO nicer API for this
    try: 
        iplatlonrtt = request.GET.get('q')
        ip,lat,lon,min_rtt = iplatlonrtt.split('|')
    except: return HttpResponse("need q query parameter and ip|lat|lon|min_rtt separated by '|'")
    return HttpResponse(
        "%s %s %s %s" % ( ip,lat,lon,min_rtt ),
        content_type="text/html"
    )

def ipmeta(request):
    ## find all related info for a list of IP addresses
    # returns a dictionary with the associated info
    try: ip_addr = request.GET.get('ip')
    except:
        return HttpResponse("no ip")
    ## normalize
    ip_addr = str( ipaddress.ip_address( ip_addr ) )
    ## lookup
    ipm,is_created = IPMeta.objects.get_or_create(ip=ip_addr,invalidated=None)
    info = ipm.info2json()
    return HttpResponse(
        json.dumps(info, indent=2),
        content_type="application/json"
    )

def ipmap(request):
    try: ip_addr = request.GET.get('ip')
    except:
        return HttpResponse("no ip")
    ## normalize
    ip_addr = str( ipaddress.ip_address( ip_addr ) )
    return render_to_response(
        'ipmap.html',
        {'ip': ip_addr}
    )

@login_required
def tracemap(request,**kwargs):
    template='oim/tracemap.html'
    #try: msm_id = int(request.GET.get('msm_id'))
    #except:
    #    ##TODO page with suggestions for msm_ids
    #    return HttpResponse("no msm_id")
    return render_to_response(
        template,
        {'queryp': request.GET.urlencode() },
        RequestContext(request)
    )

@login_required
def bulk_upload(request):
    if request.method == 'POST':
        form = ContributionUploadForm(request.POST, request.FILES)
        if form.is_valid():
            cb_list = Contribution.from_file( request.FILES['file'], request.user )
            return HttpResponse("Contribution %s received " % ( cb_list ) )
    else:
        form = ContributionUploadForm()
    return render_to_response('bulk_rules_upload.html', {'form': form}, RequestContext(request))

def domain_snippet(request):
    domain = None
    try: domain = request.GET.get('domain')
    except: pass
    token = None
    try: token = request.GET.get('token')
    except: pass
    things={}
    return HttpResponse(
        json.dumps( things , indent=2),
        content_type="application/json"
    )

@login_required
def analyse_domain(request):
    try: domain = request.GET.get('domain')
    except:
        return HttpResponse("no domain")
    hostnames = IPMeta.objects.filter(hostname__iendswith=domain).values('hostname').distinct()
    hostnames = hostnames[0:1000] # take first l000 (@@TODO make configurable)
    hostnames = [ h['hostname'] for h in hostnames]

    domain_rules = DomainRegexRule.objects.filter( user=request.user).filter( domain__endswith=domain )

    host2loc = {}

    #form = DomainRegexRuleForm(request.GET)
    #if form.is_valid():

    def apply_rules( domain_rules, h ):
        for rule in domain_rules:
            loc = apply_regex_rule_to_host( rule.regex, rule.georesult, h )
            if loc:
                return loc
        return None


    for h in hostnames:
        host2loc[h]=apply_rules( domain_rules, h )

    return render_to_response(
        'analyse_domain.html',
        {
            'domain': domain,
            'hostnames': hostnames,
            'domain_rules': domain_rules,
            'host2loc': host2loc,
        }
    )
