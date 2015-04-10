#!/usr/bin/env python
from django.core.management.base import BaseCommand, CommandError
from django.contrib.gis.geos import Point
from django.db import connection
from django.contrib.gis.measure import D ## distance
from openipmap.models import Loc,Geoalias

class Command(BaseCommand):
   args = ''
   help = 'imports Geonames worldcities database'
   def handle(self, *args, **options):
      ''' 
      Update the 'count' field in the location table
      '''
      cursor = connection.cursor()
      cursor.execute('select lat,lon,canonical_georesult,count(*) from openipmap_hostnamerule where lat is not null group by lat,lon,canonical_georesult order by count desc');
      citycounts = {}
      for row in cursor:
         (lat,lon,c1name,count) = row
         pnt = Point(lon,lat)
         cities = Loc.objects.filter( point__distance_lte=(pnt, D(km=20))).order_by( '-pop' )
         if len(cities) < 1:
            #print u"nothing for %s %s %s %s" % ( lat,lon,count,name)
            continue
         selected_city = cities[0]
         if len(cities) > 1:
            ## do city selection
            want_this_name = c1name.split(',')[0]
            for pot_city in cities:
               potential_city_name = pot_city.name.split(',')[0]
               if potential_city_name == want_this_name:
                  selected_city = pot_city
                  break
         ##print u"SELECTION for %s %s %s %s||" % (lat,lon,count,want_this_name), str(selected_city)
         if not selected_city.id in citycounts:
            citycounts[ selected_city.id ] = 0
         citycounts[ selected_city.id ] += count
      Loc.objects.filter(count__gt=0).update(count=0) 
      for city_id,count in citycounts.iteritems():
         city = Loc.objects.get(pk=city_id)
         city.count = count
         city.save()
