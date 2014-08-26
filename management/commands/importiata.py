#!/usr/bin/env python
import csv
from django.core.management.base import BaseCommand, CommandError
from routergeoloc.models import Loc,Geoalias
import re
import urllib

## iata file not always according to any standard I could find
ccmap = {
  'United States': 'us',
  'France': 'fr',
  'Canada': 'ca',
  'United Kingdom': 'gb',
  'Cote d\'Ivoire': 'ci',
  'Egypt': 'eg',
  'Greece': 'gr',
  'Ireland': 'ie',
  'Jamaica': 'jm',
  'South Africa': 'za',
  'Sri Lanka': 'lk',
  'Ukraine': 'ua',
  'Chile': 'cl',
  'Cuba': 'cu',
  'Libya': 'ly',
  'Philippines': 'ph',
  'Bolivia': 'bo',
  'New Zealand': 'nz',
  'Italy': 'it',
  'Mexico': 'mx',
  'Venezuela': 've',
  'Argentina': 'ar',
  'India': 'in',
  'China': 'cn',
  'Brazil': 'br',
  'Spain': 'es',
  'Australia': 'au',
  'Peru': 'pr',
  'Pakistan': 'pk'
}

cityalias = {
    'newyork': 'newyorkcity',
    'washington': 'washingtondc',
}

iata2locid = { ### manual corrections of inferrences below
    'mrs': 2995469,
    'mil': 3173435,
    'fco': 3169070,
    'nap': 3172394,
    'vce': 3164603,
    'trn': 3165524,
    'lux': 2960316,
    'fra': 2925533,
    'dus': 2934246,
    'gva': 2660646,
    'dfw': 4684888, ## probably better to link to both dallas AND fort worth?
    'ewr': 5101798,
    'mci': 4393217, ## this is in MO, NOT kansascity,KS,us
    'cle': 5150529,
    'msn': 5261457,
    'pdx': 5746545,
    'dub': 2964574,
    'mmx': 2692969,
    'alb': 5106834,
    'anr': 2803138,
    'gru': 3448439,
    'lin': 3173435
    # 
    # NOT:sjo
    # thr(tehran) fjr (fujeira)
}



class Command(BaseCommand):
   args = ''
   help = 'imports worldcities database'
   def handle(self, *args, **options):
      ### remove all iata ojects first
      Geoalias.objects.filter(kind__exact='iata').delete()
      count=0
      miscount=0
      ## import exceptions first
      for iata_code in iata2locid:
            loc_id = iata2locid[iata_code]
            g=Geoalias(
                loc_id=loc_id,
                word=iata_code,
                kind='iata',
                count=0
            )
            g.save()
            count += 1
      with open('./routergeoloc/data/airports.dat', 'rb') as csvfile:
         reader = csv.reader(csvfile)
         for row in reader:
            if len( row ) < 5:
               print "not using %s" % ( row )
               continue
            if row[4] and len( row[4] ) == 3:
               iata_code = row[4].lower()
               if iata_code in iata2locid: # these have already been processed
                    continue

               city_name=row[2]
               city_name = re.sub('[^a-z]','', city_name.lower() )
               if city_name in cityalias: # manual patching
                    print "citypatch %s -> %s" % ( city_name , cityalias[city_name] )
                    city_name = cityalias[city_name]

               country=row[3]
               lat = float(row[6])
               lon = float(row[7])
               geoalias_list = Geoalias.objects.filter(word__exact=city_name).filter(kind__exact='full')
               # print "%s: %s, %s, %s" % ( iata_code, city_name, country, loc_list )
               ### @@TODO control by country
               #if (len( loc_list ) == 1):
               if (len( geoalias_list ) == 1):
                  g=Geoalias(
                     loc=geoalias_list[0].loc,
                     word=iata_code,
                     kind='iata',
                     count=0
                  );
                  g.save()
                  count += 1
                  continue
               loc_id_list = [obj.loc_id for obj in geoalias_list]
               #loc_list = Loc.objects.filter(name__exact=city_name)
               loc_list = Loc.objects.filter(id__in=loc_id_list)
               if len( loc_list) > 1 and country in ccmap:
                  f_loc_list = loc_list.filter( country__exact= ccmap[ country ] )
                  if len( f_loc_list ) == 1:
                     g=Geoalias(
                        loc=f_loc_list[0],
                        word=iata_code,
                        kind='iata',
                        count=0
                     )
                     g.save()
                     count += 1
                     continue
               if len( loc_list ) == 0:
                  alt_name_list = Geoalias.objects.filter(kind__exact='full-alternate',word__exact=city_name)
                  print "%s: altlist %s" % ( city_name, alt_name_list )
                  if len( alt_name_list ) == 1:
                     g=Geoalias(
                        loc=alt_name_list[0].loc,
                        word=iata_code,
                        kind='iata',
                        count=0
                     )
                     g.save()
                     count += 1
                     continue
               print "No city for: %s: %s, %s, %s" % ( iata_code, city_name, country, loc_list )
               miscount += 1
      print "total count: %s / not inserted: %s " % ( count , miscount )
