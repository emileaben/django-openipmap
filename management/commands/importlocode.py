#!/usr/bin/env python
import gzip
from django.core.management.base import BaseCommand, CommandError
from routergeoloc.models import Loc,Geoalias
import re
import csv
from StringIO import StringIO
from zipfile import ZipFile
import urllib

DB_URL='http://www.unece.org/fileadmin/DAM/cefact/locode/loc132csv.zip';

def geo_str( coord_str ):
   coords = []
   for ll in coord_str.split(' '):
      d = ll[-1]
      deg_str = int( ll[:-1])
      sign = 1
      if d == 'S' or d == 'W':  
         sign = -1
      deg = deg_str / 100
      mins = deg_str % 100
      coords.append( sign * ( deg + ( mins/60.0 ) ) )
   return coords

def add_geoalias( loc, word, country ):
   g=Geoalias(
      loc=loc,
      word=word,
      kind='locode',
      country=country,
      count=0
   );
   g.save()

class Command(BaseCommand):
   args = ''
   help = 'imports UN Locodes database'
   def handle(self, *args, **options):
      url = urllib.urlopen( DB_URL )
      zipfile = ZipFile(StringIO(url.read()))
      count=0
      for csv_file in [f for f in zipfile.namelist() if 'csv' in f]:
         with zipfile.open( csv_file ) as fh:
            for row in csv.reader( fh ):
               if len( row ) < 4: continue
               ### @@todo not ingnore line 0
               country = row[1].lower()
               locode = row[2].lower()
               name = re.sub(r'\s+\(.*\)','', row[4]) ## alternative spellings are in () # @@ todo recognize these
               city_norm = re.sub(r'[^a-z]','', name.lower() )
               region = row[5] 
               ### @@todo range search for coordinate?
               #if len(row[10]) > 0:
               #   (lat,lon) = geo_str( row[10] )
               #   print "%s %s %s %s" %  (normalized_name, row[10], lat, lon)
               loc_list = Loc.objects.filter( name__exact=city_norm, country__exact=country )
               ## @@todo region parsing
               if len( loc_list ) == 1:
                  add_geoalias( loc_list[0], locode, country )
                  count+=1
      print "records added: %s" % (count)

'''
['', 'CD', '', '.CONGO, THE DEMOCRATIC REPUBLIC OF THE', '', '', '', '', '', '', '', '']
['', 'CD', 'ANG', 'Ango', 'Ango', '', '--3-----', 'RL', '0701', '', '0401N 02552E', '']
['', 'CD', 'ARU', 'Aru', 'Aru', 'OR', '--3-----', 'RL', '1207', '', '0252N 03050E', '']
['', 'CD', 'BNW', 'Banana', 'Banana', '', '1-3-----', 'RL', '0701', '', '0601N 01224E', '']

         loc_list = Loc.objects.filter(name__exact=city_norm)
         if len( loc_list ) ==1:
            g=Geoalias(
               loc=loc_list[0],
               word=clli,
               kind='clli',
               count=0
            );
            g.save()
            count += 1
         elif len(loc_list) > 1:
            f_loc_list = loc_list.filter( country__exact=country )
            if len( f_loc_list ) == 1:
               g=Geoalias(
                  loc=f_loc_list[0],
                  word=clli,
                  kind='clli',
                  count=0
               );
               g.save()
               count += 1
            else:
               print "no match (after tie-down to country) %s: %s, %s, %s" % ( clli, city_norm, country, loc_list )
         elif len(loc_list) == 0:
            approx_list = Loc.objects.filter( name__contains=city_norm, country__exact=country )
            if len( approx_list ) == 1:
               g=Geoalias(
                  loc=approx_list[0],
                  word=clli,
                  kind='clli',
                  count=0
               );
               g.save()
               count += 1
            else:
               print "no match (after approx+country) %s: %s, %s, %s" % ( clli, city_norm, country, loc_list )
         else:
            print "no match %s: %s, %s, %s" % ( clli, city_norm, country, loc_list )


'''
