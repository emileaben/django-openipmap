from geopy import geocoders
from geopy.distance import great_circle

## memoizer for direct_loc_resolve
class memoize(dict):
    def __init__(self, func):
        self.func = func

    def __call__(self, *args):
        return self[args]

    def __missing__(self, key):
        result = self[key] = self.func(*key)
        return result

@memoize
def loc_resolve( geocodable_string ):
    '''
    resolve any string using geonames geocoder. output the most populous place found
    '''
    # see http://www.geonames.org/export/codes.html
    ##city_fcodes=set(['PPL','PPLC','PPLA','PPLA2','PPLA3','PPLA4','PPLG','PPLS'])
    # better use 'fcl'='P' (as below)
    ## @@todo: make username configurable
    gn = geocoders.GeoNames(username="emileaben")
    locs = None
    # remove '?' and ' ' from name (they can be used as meta-info in webforms)
    geocodable_string = geocodable_string.lstrip(' ?')
    try:
        locs = gn.geocode( geocodable_string , exactly_one=False, timeout=3)
    except:
        pass
    if not locs:
        return None
    elif len( locs ) == 1:
        return locs[0]
    elif len( locs ) > 1:
        locs = [l for l in locs if 'fcl' in l.raw and l.raw['fcl'] == 'P' ]
        #locs.sort(key=lambda x: x.raw['population'],reverse=True)
        #print "%s (%s) vs %s (%s)" % ( locs[-2], locs[-2].raw['population'], locs[-1], locs[-1].raw['population'] )
        if len( locs ) > 0:
            return locs[0]
        else:
            return None
    else:
        return None

def can_one_travel_distance_in_rtt( lat1, lon1, lat2, lon2, rtt ):
   '''
     given 2 points, and a rtt, return if it is possible to travel
     that distance in fibre with the given RTT or not 
     Returns False if the distance isn't possible to travel with the
     given RTT
   '''
   km = great_circle((lat1,lon1),(lat2,lon2)).kilometers
   ## print "KM %s RTT:%s" % (km, rtt*100)
   ## use rule of thumb 100 km = 1 ms in fibre
   if float(km) > float(rtt*100):
      return False
   else:
      return True
