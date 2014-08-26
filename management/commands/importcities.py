#!/usr/bin/env python
import gzip
from django.core.management.base import BaseCommand, CommandError
from openipmap.models import Loc,Geoalias
import re
from StringIO import StringIO
from zipfile import ZipFile
import urllib

DB_URL='http://download.geonames.org/export/dump/cities15000.zip'

class Command(BaseCommand):
   args = ''
   help = 'imports Geonames worldcities database'
   def handle(self, *args, **options):
      url = urllib.urlopen( DB_URL )
      zipfile = ZipFile(StringIO(url.read()))
      Loc.objects.all().delete()
      Geoalias.objects.filter(kind='full').delete()
      for line in zipfile.open( zipfile.namelist()[0] ).readlines():
         line=line.rstrip('\n')
         (geonameid,name,asciiname,alternatenames,latitude,longitude,feature_class,feature_code,country_code,cc2,admin1_code,admin2_code,admin3_code,admin4_code,population,elevation,dem,timezone,modification_date) = line.split('\t')
         normalized_name = re.sub(r'[^a-z]','',asciiname.lower() )
         try:
            if ( int(population) < 25000 ): continue
            st_point = 'POINT(%s %s)' % (longitude, latitude)
            l=Loc(
               id=geonameid,
               # name=normalized_name,
               name=name,
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
            print "better errorhandling dude! %s" % ( line )
