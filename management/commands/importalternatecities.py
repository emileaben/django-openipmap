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

class Command(BaseCommand):
   args = ''
   help = 'imports Geonames worldcities database'
   def handle(self, *args, **options):
      url = urllib.urlopen( DB_URL )
      zipfile = ZipFile(StringIO(url.read()))
      #loc_set = set( Loc.objects.values_list('id', flat=True).order_by('id') )
      loc_dict = dict( (o.id, o.name) for o in Loc.objects.all() )
      ## flush before reimporting
      Geoalias.objects.filter(kind__exact=GEOALIAS_TYPE).delete() 
      not_count=0
      count=0
      for line in zipfile.open( ARCHIVE_NAME ).readlines():
         line=line.rstrip('\n')
         (altid,geonameid,lang,altname,is_pref,is_short,is_colloq,is_historic) = line.split('\t')
         geonameid = int(geonameid)
         if geonameid in loc_dict and lang in lang_set:
            norm_altname = routergeoloc.utils.normalize_name( altname )
            if loc_dict[geonameid] != norm_altname and len( loc_dict[geonameid] ) > 0:
               print "diff %s %s %s -> %s" % ( geonameid, lang, loc_dict[geonameid], norm_altname )
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
         else:
            not_count+=1
      print "yes:%s  no:%s" % ( count, not_count )

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
