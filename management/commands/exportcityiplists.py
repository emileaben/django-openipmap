#!/usr/bin/env python
from django.core.management.base import BaseCommand, CommandError
from openipmap.models import IPMeta,HostnameRule,IPRule
from datetime import datetime
from django.db import connection
import json

# number of cities to report on
topN=10

def find_top_cities( N ):
   cursor = connection.cursor()
   cursor.execute("select count(*),canonical_georesult from openipmap_hostnamerule where canonical_georesult != '' and age(created) < '12w' group by canonical_georesult order by count desc limit 10")
   rows = cursor.fetchall()
   cities = []
   for r in rows:
      cities.append( r[1] )
   return cities

class Command(BaseCommand):
   args = ''
   help = 'exports the IP address lists for the top X cities'
   now = datetime.today()
   def handle(self, *args, **options):
      # Pick up top X cities
      topcities = find_top_cities( topN )
      data_out = {}
      for tc in topcities: 
         city_ips=set()
         hnr = HostnameRule.objects.filter(canonical_georesult=tc)
         for h in hnr:
            ipm_list = IPMeta.objects.filter(hostname=h.hostname)
            for ipm in ipm_list:
               city_ips.add( ipm.ip )
         data_out[tc] = list( city_ips )
      print json.dumps( data_out )
