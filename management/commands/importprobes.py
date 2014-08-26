#!/usr/bin/env python
from django.core.management.base import BaseCommand, CommandError
from routergeoloc.models import Probe
import urllib2
import simplejson

#ATLAS_URL = 'https://atlas.ripe.net/'
ATLAS_URL = 'https://193.0.6.158/'


def parse_probe_json( batch ):
   if not 'objects' in batch: return
   for prb_info in batch['objects']:
      prb_id = prb_info['id']
      lat = prb_info['latitude']
      lon = prb_info['longitude']
      geo_spec = 'POINT(%s %s)' % ( lon, lat )
      p,is_created=Probe.objects.get_or_create(
        id=prb_id,
        defaults={'lat': lat, 'lon': lon, 'point': geo_spec }
      )
      if lat == -78:
        p.has_incorrect_geoloc = True
      if not is_created:
        p.lat = lat
        p.lon = lon
        p.point = geo_spec
      p.save()
      print "XX %s" % ( prb_info )

class Command(BaseCommand):
   args = ''
   help = 'imports probe locs from atlas'
   def handle(self, *args, **options):
      start_url = '%s/api/v1/probe/?limit=1000' % ( ATLAS_URL )
      req = urllib2.Request( start_url )
      req.add_header("Content-Type", "application/json")
      req.add_header("Accept", "application/json")
      conn = urllib2.urlopen(req)
      probe_data_batch = simplejson.load(conn)
      parse_probe_json( probe_data_batch )
      while True:
         if not 'meta' in probe_data_batch: break
         if not 'next' in probe_data_batch['meta']: break
         next_url = "%s%s" % ( ATLAS_URL , probe_data_batch['meta']['next'])
         next_req = urllib2.Request( next_url )
         next_req.add_header("Content-Type", "application/json")
         next_req.add_header("Accept", "application/json")
         next_conn = urllib2.urlopen(next_req)
         probe_data_batch = simplejson.load( next_conn )
         parse_probe_json( probe_data_batch )

'''
      url = urllib.urlopen( DB_URL )
      for line in zipfile.open( zipfile.namelist()[0] ).readlines():
         line=line.rstrip('\n')
         (geonameid,name,asciiname,alternatenames,latitude,longitude,feature_class,feature_code,country_code,cc2,admin1_code,admin2_code,admin3_code,admin4_code,population,elevation,dem,timezone,modification_date) = line.split('\t')
         normalized_name = re.sub(r'[^a-z]','',asciiname.lower() )
         try:
            if ( int(population) < 25000 ): continue
            st_point = 'POINT(%s %s)' % (longitude, latitude)
            l=Loc(
               id=geonameid,
               name=normalized_name,
               country=country_code.lower(),
               region=admin1_code,
               pop=population,
               lat=latitude,
               lon=longitude,
               point=st_point,
               granularity='I', ## CITY level
               count=0
            )
            l.save()
            g=Geoalias(
               loc=l,
               word=normalized_name,
               kind='full',
               count=0
            );
            g.save()
         except:
            pass
'''
