#from django.db import models
from django.contrib.gis.db import models
import re
import urllib2
import json
import time
from django.contrib.gis.measure import D
from datetime import datetime, timedelta
import dns.resolver
from publicsuffix import PublicSuffixList
from django.contrib.auth.models import User
from netfields import CidrAddressField, NetManager
import csv
import openipmap.geoutils
#import logging
#logging.basicConfig(filename='/tmp/emile.debug.log',level=logging.DEBUG)

#from routergeoloc.profile import *

### crowdsourcing part

## allow values from 0 - 100
CONFIDENCE_CHOICES = zip( range(0,101), range(0,101) )

class Contribution(models.Model):
    #our abstract base class
    #description = models.TextField()
    user = models.ForeignKey( 'auth.User' )
    #user_role = models.CharField( max_length=64 )
    created = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    deleted = models.DateTimeField(null=True, blank=True)
    confidence = models.PositiveSmallIntegerField( choices=CONFIDENCE_CHOICES, default=25 )
    class Meta:
        abstract = True
        ordering = ['-created']
    @classmethod
    def from_file( cls, file, user, dup_action='replace' ):
        '''
        returns a list of user contributions from the given file and user
        dup_action defines what happens in for a given resource/user there already exists an entry. either:
         'replace': replaces with the existing data in the new (default)
         'append':  appends (end) the existing data @@todo
         'prepend': prepends (start) the existing data @@todo
        '''
        def normalize_input( str ):
            re.sub('^\s+','',str)
            re.sub('\s+$','',str)
            re.sub('"','',str)
            return str
        ##TODO return some stats on the insert
        ##TODO have a single CREATED time for a submission
        # so, a submission can be characterised by <user/created_time>
        # created_time=datetime.datetime.now()
        # for now this doesn't work because created is auto_now_add (so not editable)
        dialect = csv.Sniffer().sniff(file.read(1024))
        file.seek(0)
        rulereader = csv.reader(file, dialect)
        seen_domain={} # list domains already seen/useful for when replacing whole domain
        for row in rulereader:
            if len( row ) < 3:
                ## ignore, TODO: do a count of how often this happens?
                continue
            if re.match('^#', row[0]):
                # or save to descr?
                continue
            if row[0] == 'domain_regex': #@@ for now only domain rule-types   and re.match('[a-zA-Z\.\d]+',row[1]):
                try:
                    domain=row[1]
                    #domain = normalize_input( row[1] )
                    try:
                        if not domain in seen_domain:
                            if dup_action == 'replace':
                                DomainRegexRule.objects.filter( user=user).filter( domain=domain ).delete()
                            seen_domain[ domain ] = 1
                    except:
                        raise Exception("removing older objects related to this bulk upload failed")
                    r_rule=DomainRegexRule(
                        domain=    domain,
                        user=      user,
                        regex=     row[2],
                        georesult=    row[3],
                        confidence=int(row[4]),
                        created=created_time,
                    )
                except:
                    raise Exception("domain_regex rule creation failed for '%s'" % ( row ) )
                try:
                    r_rule.save()
                except:
                    raise Exception("Saving rule failed for '%s / '%s''" % ( row, r_rule ) )
            elif re.match(r'^[0-9\.\/]$',row[0]) or re.match(r'^[0-9a-fA-F\:\.\/]+$',row[0]):
                iprule=IPRule(
                    ip=row[0],
                    georesult=row[1],
                    user=user,
                    confidence=int(row[2])
                )
                iprule.save()
            else:
                hostnamerule=HostnameRule(
                    hostname=row[0],
                    georesult=row[1],
                    user=user,
                    confidence=int(row[2])
                )
                hostnamerule.save()
                #assume it's an exact hostname
        # do I have to close the file?
        return ["aaah"];

class HostnameRule( Contribution ):
    hostname = models.CharField( db_index=True, max_length=256 )
    georesult = models.CharField( max_length=256, blank=True, null=True )
    canonical_georesult = models.CharField( max_length=256, blank=True, null=True)
    #granularity = models.CharField(max_length=1,  choices=GRANULARITIES ) default city for now
    lat = models.FloatField(blank=True,null=True )
    lon = models.FloatField(blank=True,null=True )

    def save( self, *args, **kwargs ):
        if self.georesult:
            loc = openipmap.geoutils.loc_resolve( self.georesult )
            if loc and loc.raw['lat'] and loc.raw['lng']:
                self.lat = loc.raw['lat']
                self.lon = loc.raw['lng']
                cityname = ''
                try: cityname = loc.raw['name']
                except: pass
                regionname = ''
                try: regionname = loc.raw['adminName1']
                except: pass
                countrycode = ''
                try: countrycode = loc.raw['countryCode']
                except: pass
                self.canonical_georesult = "%s,%s,%s" % ( cityname, regionname, countrycode )
        super(HostnameRule, self).save(*args, **kwargs)

    @classmethod
    def get_crowdsourced(cls,hostname,max_results=10):
        '''
        TODO: Move usage of this to the API
        returns list of 'max_results' number of results for this particular hostname from the HostnameRule tables
        '''
        results = []
        hnr=HostnameRule.objects.filter( hostname=hostname )
        for rule in hnr:
            results.append({
                'kind':'hostname',
                'granularity':'city',
                'lat': rule.lat,
                'lon': rule.lon,
                'georesult': rule.georesult,
                'canonical_georesult': rule.canonical_georesult,
                'confidence': rule.confidence
            });
        return results

# may not be needed:
#class IPRuleManager( NetManager, models.GeoManager ):
#    pass

class IPRule( Contribution ):
    #ip = models.GenericIPAddressField()
    ip = CidrAddressField()
    georesult = models.CharField( max_length=256 )
    canonical_georesult = models.CharField( max_length=256, blank=True, null=True)
    #granularity = models.CharField(max_length=1,  choices=GRANULARITIES ) default city for now
    lat = models.FloatField(blank=True,null=True )
    lon = models.FloatField(blank=True,null=True )

    objects = NetManager()
    #objects = IPRuleManager()

    def save( self, *args, **kwargs ):
        if self.georesult:
            loc = openipmap.geoutils.loc_resolve( self.georesult )
            if loc and loc.raw['lat'] and loc.raw['lng']:
                self.lat = loc.raw['lat']
                self.lon = loc.raw['lng']
                cityname = ''
                try: cityname = loc.raw['name']
                except: pass
                regionname = ''
                try: regionname = loc.raw['adminName1']
                except: pass
                countrycode = ''
                try: countrycode = loc.raw['countryCode']
                except: pass
                self.canonical_georesult = "%s,%s,%s" % ( cityname, regionname, countrycode )
        super(IPRule, self).save(*args, **kwargs)


    @classmethod
    def get_crowdsourced(cls,ip,max_results=10):
        '''
        returns 'max_results' number of results for this particular IP from the IPRules tables
        '''
        results=[]
        ipr=IPRule.objects.filter(ip__net_contains_or_equals=ip)
        for rule in ipr:
            results.append({
                'kind': 'ip',
                'granularity': 'city',
                'lat': rule.lat,
                'lon': rule.lon,
                'georesult': rule.georesult,
                'canonical_georesult': rule.canonical_georesult,
                'confidence': rule.confidence,
            });
        return results

class DomainRegexRule( Contribution ):
    domain = models.CharField( max_length=256 )
    regex = models.CharField( max_length=1024 )
    georesult = models.CharField( max_length=256 )
    order = models.IntegerField(null=True, blank=True)

POSITION_TYPE_CHOICES = (
    (u'START', u'Match start of FQDN'),
    (u'LABEL', u'Match a specific DNS label'),
    (u'WORD',  u'Match a specific word [a-zA-Z]'),
    (u'CHAR',  u'Match a specific character position'),
## add more maybe??
)

class DomainTagRule( Contribution ):
    '''
    position_type: easy concept of where this tag is in the domainname
    position: depending on position_type, the position where the tag is in. null means figure it out yourself
    '''
    domain = models.CharField( max_length=256 )
    tag = models.CharField( max_length=256 )
    georesult = models.CharField( max_length=256 )
    position_type = models.CharField( choices=POSITION_TYPE_CHOICES, null=True, blank=True, max_length=10 )
    position = models.IntegerField(null=True, blank=True)


class ASNRule( Contribution ):
    asn = models.IntegerField()
    georesult = models.CharField( max_length=256 )

########## END crowdsourcing part

GRANULARITIES=(
   (u'C', u'Country'),
   (u'I', u'City'),
   (u'D', u'Datacentre'),
)

# Create your models here.
class Loc(models.Model):
   name = models.CharField( max_length=256 )
   region = models.CharField( max_length=256 )
   country = models.CharField( max_length=2 )
   granularity = models.CharField(max_length=1,  choices=GRANULARITIES )
   lat = models.FloatField()
   lon = models.FloatField()
   pop = models.IntegerField()
   count = models.IntegerField( default=0 )
   # GIS extension
   point = models.PointField()
   objects = models.GeoManager()

   def __unicode__(self): return "%s,%s,%s" % ( self.name, self.region, self.country )
   #class Meta:
   #   ordering = ["name","country"]

   def normalize_name( name ):
      name = re.sub(r'[^a-z]+','',name)
      return name

#class Word(models.Model):
#   word = models.CharField( max_length=256 )
#   locs = models.ManyToManyField(Loc, through='Geoalias')
#   def __unicode__(self): return self.word

class Geoalias(models.Model):
   loc = models.ForeignKey( Loc, blank=True, null=True )
   word = models.CharField( db_index=True, max_length=256 )
   kind = models.CharField( max_length=128 )
   lang = models.CharField( max_length=8, blank=True, null=True )
   country = models.CharField( max_length=8, blank=True, null=True )
   count = models.IntegerField( default=0 )
   def __unicode__(self): return "%s (%s : %s)" % (self.word, self.loc, self.kind )
   class Meta:
      verbose_name_plural = 'geoaliases'
      #ordering = ["word","kind"]

class IPMeta(models.Model):
    ip = models.GenericIPAddressField( db_index=True )
    created = models.DateTimeField( auto_now_add=True )
    invalidated = models.DateTimeField( blank=True, null=True, db_index=True )
    last_updated = models.DateTimeField(auto_now=True)
    dnsloc = models.CharField( max_length=256, blank=True, null=True )
    hostname = models.CharField( max_length=256, blank=True, null=True )
    ##is_anycast = models.NullBooleanField( blank=True, null=True )

    psl = PublicSuffixList()

    def save(self, **kwargs):
        ''' IPMeta save method, does lookups if object isn't saved yet '''
        if not self.id:
            ## do dnsloc and hostname lookups
            try:
                host_resolve = dns.resolver.query(dns.reversename.from_address( self.ip ),'PTR')
                h = str(host_resolve.response.answer[0].items[0])
                h = h.rstrip('.')
                self.hostname = h
            except: #it's perfectly fine for a reverse not to exist
                pass
            if self.hostname:
                try:
                    loc_resolve = dns.resolver.query( self.hostname, 'LOC')
                    self.dnsloc = str( loc_resolve[0] )
                except: # it's perfectly fine for a loc record not to exist
                    pass
        super(self.__class__, self).save(**kwargs)

    def info2json(self):
        DNSLOC_WEIGHT=0.95
        HOSTNAME_WEIGHT=0.90
        # 0  1  2      3 4 5  7     7
        # 48 51 21.953 N 2 23 0.143 E 10.00m 1.00m 10000.00m 10.00m"
        def _dnsloc2ll( loc_str ):
            out = {'str': loc_str}
            fields = loc_str.split()
            if len(fields) >= 7:
                lat = float(fields[0]) + float(fields[1])/60 + float(fields[2])/(60*60)
                if fields[3] == 'S': lat = -lat
                lon = float(fields[4]) + float(fields[5])/60 + float(fields[6])/(60*60)
                if fields[7] == 'W': lon = -lon
                out['lat'] = lat
                out['lon'] = lon
            return out
        info = {}
        name2loc=[]
        crowdsourced=[]
        info['ip'] = self.ip
        info['hostname'] = self.hostname
        info['domainname'] = None
        try:
            info['domainname'] = self.__class__.psl.get_public_suffix( self.hostname )
        except: pass
        if self.dnsloc:
            info['dnsloc'] = _dnsloc2ll( self.dnsloc )
        #gc = IPGeoConstraint.objects.filter(ipmeta = self)
        #if len( gc ) == 1:
        #    info['area'] = json.loads( gc[0].area.geojson )
        ## add a suggestions array that contains the ordered list of suggested lat/lon
        suggestions = []
        name2loc = self.name2loc()
        if 'dnsloc' in info:
            suggestions.append({
                'lat': info['dnsloc']['lat'],
                'lon': info['dnsloc']['lon'],
                'reason': 'dnsloc',
                'weight': DNSLOC_WEIGHT,
            });
        total_pop = 0;
        for n in name2loc:
            total_pop += n['pop']
        for n in name2loc:
            # lat/lon already there
            n['weight'] = HOSTNAME_WEIGHT * n['pop']/total_pop
            n['reason'] = 'hostname'
            suggestions.append( n )
        info['suggestions'] = suggestions
        crowdsourced.extend( IPRule.get_crowdsourced( self.ip ) )
        if self.hostname:
            crowdsourced.extend( HostnameRule.get_crowdsourced( self.hostname ) )

        info['crowdsourced'] = crowdsourced
        return info

    def name2loc(self, poly_geoconstraint=None):
        '''try to figure out loc, based on name'''
        ## TODO: add polygon confinement?
        nr_results=10 ## configurable?

        # this should be configurable/tags and/or have low confidence value
        tag_blacklist=set(['rev','cloud','clients','demarc','ebr','pool','bras','core','static','router','net','bgp','pos','out','link','host','infra','ptr','isp','adsl','rdns','tengig','tengige','tge','rtr','shared','red','access','tenge','gin','dsl','cpe'])

        if not self.hostname: return []
        name = self.hostname.rstrip('.')
        suf = self.__class__.psl.get_public_suffix( name )
        rest = ''
        tokens = []
        if suf != name:
            rest = name[0:len(name)-len(suf)-1]
            rest = rest.lower()
            ## support for additional tokenization?
            tokens = re.split(r'[^a-zA-Z]+',rest)
            ## filter by token-length (for now) , TODO make configurable?
            tokens = [t for t in tokens if len(t) >= 3]
            ## remove blacklisted tokens
            tokens = [t for t in tokens if not t in tag_blacklist]

        matches = {}
        def add_to_matches( g, token, is_abbrev ):
            if not g.loc.id in matches:
                matches[g.loc.id] = {
                    'loc_id': g.loc.id,
                    'pop': g.loc.pop,
                    'name': str( g.loc ),
                    'lat': g.loc.lat,
                    'lon': g.loc.lon,
                    'token': set(),
                    'kind': set()
                }
                if poly_geoconstraint:
                    if poly_geoconstraint.contains( g.loc.point ):
                        matches[g.loc.id] = { 'in_constraint': True }

            matches[g.loc.id]['token'].add( token )
            ## this loses the link between the token and the geoalias-kind (for now)
            if is_abbrev:
                matches[g.loc.id]['kind'].add( 'abbrev-' + g.kind )
            else:
                matches[g.loc.id]['kind'].add( g.kind )

        for t in tokens:
            for ga in Geoalias.objects.filter(word=t):
                add_to_matches( ga, t, False )
        if len( matches ) == 0:
            #print "little on strict match, trying like"
            for t in tokens:
                ## 't' can't be anything but a-zA-Z so no SQL injection possible
                sql_like_chars = '%%'.join( list( t ) )
                sql_like_chars += '%%'
                # 'a%m%s%'
                sql = "SELECT id FROM openipmap_geoalias WHERE word LIKE '%s'" % ( sql_like_chars )
                for ga in Geoalias.objects.raw( sql ):
                    add_to_matches( ga, t, True )
        mk = sorted( matches.keys(), reverse=True, key=lambda x: matches[x]['pop'] )[0:nr_results] ## max 10
        result = []
        for m in mk:
            entry = matches[m]
            # flatten
            entry['token'] = list( entry['token'] )
            entry['kind'] = list( entry['kind'] )
            result.append( entry )
        return result

    @classmethod
    def gather_from_msm(self, msm_id, interval=3600):
        #@@ todo make these configurable:
        limit=10
        stop=int(time.time())
        start = stop - interval

        msm_url = "https://atlas.ripe.net/api/v1/measurement/%d/result/?start=%d&stop=%d&limit=%d&format=txt" % ( msm_id, start, stop, limit )
        print msm_url
        url_fh = urllib2.urlopen( msm_url )
        ips = {}
        for line in url_fh:
            try:
                msm = json.loads( line )
                prb_id = msm['prb_id']
                for msm_res in msm['result']:
                    hop_nr = msm_res['hop']
                    for hop_res in msm_res['result']:
                        if 'from' in hop_res:
                            ip = hop_res['from']
                            rtt = hop_res['rtt']
                            if not ip in ips:
                                ips[ip] = 1
            except:
                print "oops on %s" % ( line )
        timediff = datetime.now()-timedelta( days=30 )
        for ip in ips:
            ## figure out if there is a recent Meta fetch done
            try:
                ipm = self.objects.filter( ip=ip ).filter( created__gte=timediff ).order_by('-created')
                if len( ipm ) > 0:
                    i = ipm[0]
                else:
                    ## insert it (does autolookups)
                    i = IPMeta()
                    i.ip = ip
                    i.save()
                print "%s %s %s" % ( i.ip, i.hostname, i.dnsloc )
            except:
                pass

class Probe(models.Model):
   lat = models.FloatField()
   lon = models.FloatField()
   lastmile_rtt = models.FloatField( blank=True, null=True )
   has_incorrect_geoloc = models.NullBooleanField( blank=True, null=True )
   ## GIS extensions:
   point = models.PointField()
   objects = models.GeoManager()

class IPGeoConstraint(models.Model):
    ### store constraints
    ipmeta = models.ForeignKey( IPMeta )
    area = models.PolygonField()
    created = models.DateTimeField(auto_now_add=True)
    objects = models.GeoManager()
    class Meta:
        ordering = ['-created']

 ## NOT RIGHT PLACE, but hey
class JsonRequest(urllib2.Request):
    def __init__(self, url):
        urllib2.Request.__init__(self, url)
        self.add_header("Content-Type", "application/json")
        self.add_header("Accept", "application/json")


class Triangulation(models.Model): 
    ip = models.GenericIPAddressField()
    ##MSM_BASE_FMT="https://atlas.ripe.net/api/v1/measurement/%d/result/?format=txt"
    msm_result_fmt="https://193.0.6.158/api/v1/measurement/%d/result/?format=txt"
    KM_PER_MS=100 # assuming 2 way and light in fiber is 2/3 speed of light
    msm_key='5531c157-ace1-46f2-b386-22a68b0539a6'
    msm_create_url='https://atlas.ripe.net/api/v1/measurement/?key=%s' % (msm_key)
    def _update( self ):
        ## update with msms that are not final yet
        ## @@ continue from here
        return
    def parse_msm_results( self ):
        for m in self.trimsm_set.all():
            fh=urllib2.urlopen( self.__class__.msm_result_fmt % ( m.msm ) )
            for line in fh:
                d = json.loads( line )
                if d['min'] <= 0: continue
                p = Probe.objects.get( id = d['prb_id'] )
                if p.has_incorrect_geoloc == True:
                    continue
                tric, is_created = self.triconstraint_set.get_or_create(
                    lat = p.lat,
                    lon = p.lon,
                    rtt = d['min'],
                    lastmile_rtt = p.lastmile_rtt,
                    prb = p
                )
    def refine( self ):
        self._update()
        constraints = self.triconstraint_set.all().order_by('rtt')
        af = 4
        if re.search(':', self.ip ):
            af = 6
        msm_def = {
            "definitions": [
                { "target": self.ip,
                  "description": "triangulation for %s" % self.ip,
                  "type": "ping",
                  "af": af,
                  "is_oneoff": True,
                  "packets": 5,
                }
            ],
            "probes": []
        }
        if len(constraints) ==0: ## no previous knowledge on this IP
            ### add 5 probes from each 'area'
            for area in ('West','North-Central','South-Central','North-East','South-East'):
                msm_def['probes'].append({
                    'requested': 5,
                    'type': 'area',
                    'value': area
                })
        else:
            prb_set = Probe.objects.all()
            loc_set = Loc.objects.all().order_by('-pop')
            for c in constraints:
                max_dist = c.rtt*self.__class__.KM_PER_MS
                point_rep = 'POINT(%s %s)' % ( c.lon, c.lat )
                prb_set=prb_set.filter(
                    point__distance_lt=(point_rep, D(km=max_dist) )
                )
                loc_set=loc_set.filter(
                    point__distance_lt=(point_rep, D(km=max_dist) )
                )
            print "potential locs within constraints %s" % ( len( loc_set ) )
            ## top 5 locs within set (for now ordered by population)
            prb_ids = []
            for loc in loc_set:
                ## select 3 probes close to this loc
                prb_close_to_loc = Probe.objects.filter(
                    point__distance_lt=('POINT(%s %s)' % (loc.lon, loc.lat ), D(km=100))
                ).order_by('-id')
                for p in prb_close_to_loc[0:3]:
                    prb_ids.append( str(p.id) )
                    print "added %s (%s)" % ( p.id, loc )
                if len( prb_ids ) > 20:
                    break
            msm_def['probes'].append({
                'requested': 20,
                'type': 'probes',
                'value': ",".join(prb_ids)
            })
        msm_json = json.dumps( msm_def )
        msm_req = JsonRequest( self.__class__.msm_create_url )
        try:
            msm_conn = urllib2.urlopen( msm_req, msm_json )
        except urllib2.HTTPError as e:
            print "HTTP error %s " % ( e.read )
        msm_meta = json.load(msm_conn)
        for msm_id in msm_meta['measurements']:
            self.save()
            new_trimsm = self.trimsm_set.create( msm=msm_id )
            print "msm_id created: %s" % ( msm_id )
        #msm_id = msm_meta['measurements'][0]
        ### here we save it to TriMsm
        ## self.add_msm_results( msm_id )
    def find_locs( self, max=10 ): ### very very dumb now
        self._order_constraints()
        (lat,lon,rtt,lm_rtt,prb_id) = self.constraints[0]

### these are summaries of measurement results
class TriConstraint(models.Model):
    triangulation = models.ForeignKey( Triangulation )
    lat = models.FloatField()
    lon = models.FloatField()
### geodb point?
    rtt = models.FloatField()
## captures probe status at that point in time (so copied)
    lastmile_rtt = models.FloatField( blank=True, null=True )
    prb = models.ForeignKey( Probe )
    def __unicode__(self): return "%s\t%s\t%s\t%s" % ( self.lat, self.lon, self.rtt, self.prb.id )

### holds the measurements that were done for triangulation
class TriMsm(models.Model):
    triangulation = models.ForeignKey( Triangulation )
    msm = models.IntegerField()
    status = models.CharField( max_length=32 ) ## probably have choices: 'final' or not
    created = models.DateTimeField(auto_now_add=True)

### holds results from a reverse dns
class ReverseDnsScan(models.Model):
    domain = models.CharField( max_length=128, db_index=True )
    hostpart = models.CharField( max_length=128 )
    ip = models.GenericIPAddressField( db_index=True )
