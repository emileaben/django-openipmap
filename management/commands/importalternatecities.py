#!/usr/bin/env python
import gzip
from django.core.management.base import BaseCommand, CommandError
from openipmap.models import Loc,Geoalias
import openipmap.utils
import re
from StringIO import StringIO
from zipfile import ZipFile
import urllib

DB_URL='http://download.geonames.org/export/dump/alternateNames.zip'
ARCHIVE_NAME='alternateNames.txt'

GEOALIAS_TYPE='full-alternative'

lang_set = set(['it','se','fr','es','de','','en','id',])
## ru (not translatable?)

### geonames doesn't have them all :(
# this is a iata => geonames mapping that gets imported
iata_manual_imports = {
    'iad': 4140963,
    'fco': 3169070,
    'mci': 4393217, ## this is in MO, NOT kansascity,KS,us
    'mmx': 2692969,
    'gru': 3448439,
    'lin': 3173435
}

def import_iata(geonameid,iatacode):
   g=Geoalias(
      loc_id=geonameid,
      word=iatacode.lower(),
      kind='iata',
      count=0
   )
   g.save()

class Command(BaseCommand):
   args = ''
   help = 'imports info from Geonames worldcities alternateNames database (alternative city names and iata codes)'
   def handle(self, *args, **options):
      url = urllib.urlopen( DB_URL )
      zipfile = ZipFile(StringIO(url.read()))
      #loc_set = set( Loc.objects.values_list('id', flat=True).order_by('id') )
      loc_dict = dict( (o.id, o.name) for o in Loc.objects.all() )
      ## flush before reimporting
      Geoalias.objects.filter(kind__exact=GEOALIAS_TYPE).delete() 
      Geoalias.objects.filter(kind__exact='iata').delete() 
      not_count=0
      iata_count=0
      count=0
      for line in zipfile.open( ARCHIVE_NAME ).readlines():
         line=line.rstrip('\n')
         (altid,geonameid,lang,altname,is_pref,is_short,is_colloq,is_historic) = line.split('\t')
         geonameid = int(geonameid)
         if geonameid in loc_dict and lang in lang_set:
            norm_altname = openipmap.utils.normalize_name( altname )
            if loc_dict[geonameid] != norm_altname and len( loc_dict[geonameid] ) > 0:
               #print "diff %s %s %s -> %s" % ( geonameid, lang, loc_dict[geonameid], norm_altname )
               g=Geoalias(
                  loc_id=geonameid,
                  word=norm_altname,
                  kind=GEOALIAS_TYPE,
                  lang=lang,
                  count=0
               )
               g.save()
            ## maybe compare to normal, and only insert if altname differs
            count+=1
         elif lang == 'iata' and geonameid in loc_dict:
            ## get IATA codes for geonames we have in our database
            import_iata( geonameid, altname.lower() )
            iata_count+=1
         else:
            not_count+=1
      for iata_code,geonameid in iata_manual_imports.iteritems():
            if Geoalias.objects.filter(kind__exact='iata').filter(word__exact=iata_code).count() == 0:
               import_iata( geonameid, iata_code )
               iata_count+=1
               print "didn't exist: %s -> %s" % ( iata_code, geonameid )
            else:
               print "already exists: %s -> %s" % ( iata_code, geonameid )
      print "yes:%s  no:%s iata:%s" % ( count, not_count, iata_count )

'''
         normalized_name = re.sub(r'[^a-z]','',asciiname.lower() )
         try:
            if ( int(population) < 25000 ): continue
            l=Loc(
               id=geonameid,
               name=normalized_name,
               country=country_code.lower(),
               region=admin1_code,
               pop=population,
               lat=latitude,
               lon=longitude,
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
