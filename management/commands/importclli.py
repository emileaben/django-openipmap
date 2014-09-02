#!/usr/bin/env python
from django.core.management.base import BaseCommand, CommandError
from openipmap.models import Loc,Geoalias
import re
## from collections import Counter ### python 2.6 ugh

ccmap = {
   'uk': 'gb'
}

citymap = {
   'newyork': 'newyorkcity',
   'frankfurt': 'frankfurtammain'
}

class Command(BaseCommand):
   args = ''
   help = 'imports clli codes (from peeringdb)'
   def handle(self, *args, **options):
      Geoalias.objects.filter(kind__exact='clli').delete()
      count=0
      cllis={}
      with open('./openipmap/data/cllis.txt', 'rb') as f:
         f.readline() ## remove header
         f.readline() ## remove header
         for line in f:
#            CLEVOH   Cleveland   OH US
             line = line.rstrip('\n')
             (clli,city,region,country) = line.split('\t')
             clli = clli.lower()
             clli = re.sub('[^a-z]','',clli)
             if len(clli) != 6: continue
             loc_str = '|'.join([ city.lower() , region.lower() , country.lower() ])
             if not clli in cllis:
               cllis[clli] = {}
             if not loc_str in cllis[clli]:
                cllis[clli][ loc_str ] = 1
             else:
                cllis[clli][ loc_str ] += 1
      for clli in cllis: 
         print "%s" % ( cllis[clli].items() )
         locs_sorted = sorted( cllis[clli].items() , key=lambda x:x[1], reverse=True )
         print "%s" % ( locs_sorted )
         most_common_loc = locs_sorted[0][0]
         (city,region,country) = most_common_loc.split('|')
         if country in ccmap: country = ccmap[country]
         if city in citymap: city=citymap[city]
         city_norm = re.sub('[^a-z]','',city)
         geoalias_list = Geoalias.objects.filter(word__exact=city_norm,kind__exact='full')
         loc_id_list = [obj.loc_id for obj in geoalias_list]
         loc_list = Loc.objects.filter(id__in=loc_id_list)
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
      print "total count: %s" % ( count )
'''
         for row in reader:
            if row[4] and len( row[4] ) == 3:
               city_name=row[2]
               country=row[3]
               iata_code = row[4].lower()
               lat = float(row[6])
               lon = float(row[7])
               city_name = re.sub('[^a-z]','', city_name.lower() )
               loc_list = Loc.objects.filter(name__exact=city_name)
               # print "%s: %s, %s, %s" % ( iata_code, city_name, country, loc_list )
               ### @@TODO control by country
               if (len( loc_list ) == 1):
                  g=Geoalias(
                     loc=loc_list[0],
                     word=iata_code,
                     kind='iata',
                     count=0
                  );
                  g.save()
                  count += 1
               elif len( loc_list) > 1 and country in ccmap:
                  f_loc_list = loc_list.filter( country__exact= ccmap[ country ] )
                  if len( f_loc_list ) == 1:
                     g=Geoalias(
                        loc=f_loc_list[0],
                        word=iata_code,
                        kind='iata',
                        count=0
                     );
                     g.save()
                     count += 1
               else:
                  print "No city for: %s: %s, %s, %s" % ( iata_code, city_name, country, loc_list )

      print "total count: %s" % ( count )
'''
