import unicodedata
import re
import ipaddress
from openipmap.models import Loc,Geoalias,IPMeta,Probe
import openipmap.geoutils

#import logging
#logging.basicConfig(filename='/tmp/debug.log',level=logging.DEBUG)
#LOG=logging.getLogger(__name__)

#import dns.resolver

def asciify( x ):
  if isinstance(x, str):
    x = x.decode('utf-8')
  return unicodedata.normalize('NFKD', x ).encode('ascii', 'ignore')

def normalize_name( x ):
   x = asciify( x )
   x = x.lower()
   x = re.sub(r'[^a-z]','',x)
   return x

def find_ip_info( ip_addr ):
    info = {}
    ## do we have info on this ip_addr?
    ipmeta_l = IPMeta.objects.filter(ip__exact=ip_addr)
    if len(ipmeta_l)==0:
        create_ipmeta( ip_addr )
    return info

def create_ipmeta( ip_addr ):
    dnshost = do_dns_host_lookup( ip_addr )
    if dnshost:
        dnsloc = do_dns_loc_lookup( dnshost )
    ipm=IPMeta( ##HERE
        ip=ip_addr,
        hostname=dnshost,
        dnsloc=dnsloc
    )
    ipm.save()

def do_dns_loc_lookups( ip_addr ):
    dnsloc = None
    return dnsloc

def do_dns_host_lookup( ip_addr ):
    dnshost = None
    try:
        resolve = dns.resolver.query(dns.reversename.from_address( ip_addr),'PTR')
        dnshost = str(resolve.response.answer[0].items[0])
    except:
        pass
    return dnshost


## memoizer for direct_loc_resolve
class memoize(dict):
    def __init__(self, func):
        self.func = func

    def __call__(self, *args):
        print "called %s(%s)" % (self.func.func_name, args)
        return self[args]

    def __missing__(self, key):
        result = self[key] = self.func(*key)
        return result

@memoize
def direct_loc_resolve( geocodable_string ):
    '''
    resolve any string using geonames geocoder. output the most populous place found
    '''
    # see http://www.geonames.org/export/codes.html
    city_fcodes=set(['PPL','PPLC','PPLA','PPLA2','PPLA3','PPLA4','PPLG','PPLS'])
    ## @@todo: make username configurable
    gn = geocoders.GeoNames(username="emileaben")
    locs = gn.geocode( geocodable_string , exactly_one=False)
    if not locs:
        return None
    elif len( locs ) == 1:
        return locs[0]
    else:
        locs = [l for l in locs if l.raw['fcode'] in city_fcodes ]
        locs.sort(key=lambda x: x.raw['population'])
        #print "%s (%s) vs %s (%s)" % ( locs[-2], locs[-2].raw['population'], locs[-1], locs[-1].raw['population'] )
        return locs[-1]



def apply_regex_rule_to_host( regex, sub, hostname):
    #LOG.debug("apply_regex_rule_to_host with %s %s %s" % ( regex, sub, hostname ) )
    def key_value_loc_resolve( kv_string ):
        @memoize
        def map_to_clli( clli_code ):
            geoaliases = Geoalias.objects.select_related('loc').filter(word=clli_code).filter(kind='clli')
            if len( geoaliases ) == 1: # iata code should be unique
                return geoaliases[0].loc
            else:
                return None
        @memoize
        def map_to_iata( iata_code ):
            geoaliases = Geoalias.objects.select_related('loc').filter(word=iata_code).filter(kind='iata')
            if len( geoaliases ) == 1: # iata code should be unique
                return geoaliases[0].loc
            else:
                return None
        dispatcher = {
            'iata': map_to_iata,
            'clli': map_to_clli,
        }

        key,value = kv_string.split(':',1)
        try:
            return dispatcher[key](value)
        except:
            raise Exception("location key '%s' isn't valid" % (key))
            return None

    ## check if 'sub' needs reevaluation
    is_substitution = False
    is_key_value = False
    if "\\" in sub: ## contains our substitute string
        is_substitution = True
    if ':' in sub:
        is_key_value = True

    h = hostname.lower()
    re_result = None
    if not is_substitution:
        if re.search( regex, h):
            re_result=sub
        else:
            #LOG.debug("returns: None")
            return None
    else:
        # need some delimiter to filter out only the sub rule later:
        sub = "|%s|" % (sub)
        sub_result = re.sub( regex, sub, h, count=1 )
        re_match = re.search(r'\|(.*)\|', sub_result)
        if re_match:
            re_result=re_match.group(1)
        else:
            #LOG.debug("returns: None")
            return None

    if not is_key_value:
        loc = routergeoloc.geoutils.loc_resolve( re_result )
        #LOG.debug("returns: %s" % (loc) )
        return loc
        #print "%s -> %s (id:%s) (direct)" %  ( h , loc, loc.raw['geonameId'] )
    else:
        loc = key_value_loc_resolve( re_result )
        #LOG.debug("returns: %s" % (loc) )
        return loc
        #print "%s -> %s (id:%s) (via kv)" %  ( h , loc, loc.id )

def apply_regex_rule( domain, regex, sub ):
    '''
      applies a regex_rule to things in domain. regex is the regex to apply, sub contains the result
      sub can either be a directly geolocatable string, or a hint for further processing.
      hints are key:value pairs
      sub can contain backreferences to matched things in the regex, ie. \1 \2 \3
    '''
    ##@@TODO think of security of regex (DoS and code callout)


    try:
        re_compiled = re.compile( regex )
    except:
        # needs to raise the specific error
        raise Exception("problem compiling regex '%s'" % (regex))

    domain.rstrip('.')
    result = {}
    ipm_list = IPMeta.objects.filter(hostname__iendswith="%s." % (domain) )
    for ipm in ipm_list:
        h = ipm.hostname.lower()
        h.rstrip('.')
        loc = apply_regex_rule_to_host( regex, sub, h )

        ## now tokenize into key/value pairs
        if not loc  in result:
            result[loc] = {}
        if not h in result[loc]:
            result[loc][h] = 0
        result[loc][h] += 1
    for loc in result:
        print "%s | %s" % (loc, result[loc].keys()[0] )
    #return result

def apply_tokenizer_rule( domain ):
    result = {}
    return result
