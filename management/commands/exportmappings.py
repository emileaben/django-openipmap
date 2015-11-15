#!/usr/bin/env python
from django.core.management.base import BaseCommand, CommandError
from openipmap.models import HostnameRule,IPMeta
from openipmap.utils import do_dns_host_lookup,do_dns_loc_lookup
from datetime import datetime
import pytz
import codecs
import sys

## this allows to pipe output to a file and have it be utf-8
# adapted from http://stackoverflow.com/questions/4545661/unicodedecodeerror-when-redirecting-to-file
sys.stdout = codecs.getwriter('utf-8')(sys.stdout)

def total_seconds( td ):
   return (td.microseconds + (td.seconds + td.days * 24 * 3600) * 10**6) / 10**6

def check_and_expire( ip, ipm_list ):
   ''' given an IP address and a list of IPMeta objects for that IP, expire all info in db that is not up to date '''
   print "%s %s" %  (ip, len( ipm_list ) )
   if len( ipm_list ) > 1:
      ### pick one, rest should have been invalidated anyways
      for ipm in ipm_list[1:]:
         ipm.invalidated=datetime.now(pytz.utc)
         ipm.last_updated=datetime.now(pytz.utc)
         ipm.save()
   ipm = ipm_list[0] # this is the chosen ipmeta object to validate against
   now_dnshost = None
   now_dnsloc = None
   now_dnshost = do_dns_host_lookup( ip )
   if now_dnshost != None:
      now_dnsloc = do_dns_loc_lookup( now_dnshost )
   if ipm.hostname != now_dnshost or ipm.dnsloc != now_dnsloc:
      # invalidate old and create new
      ipm.invalidated = datetime.now(pytz.utc)
      ipm.last_updated=datetime.now(pytz.utc)
      ipm.save()
      # clone didn't work ( https://docs.djangoproject.com/en/1.7/topics/db/queries/#copying-model-instances )
      # so doing a new object for now
      print "creating new! for %s/%s" % ( ipm.ip , ipm.hostname )
      ipm_new = IPMeta(
         ip= ipm.ip
      )
      ipm_new.save() ## this will do another DNS lookup (which should be in cache anyways)
   else: #save the last time this info was checked
      ipm.last_updated=datetime.now(pytz.utc)
      ipm.save()

class Command(BaseCommand):
   args = ''
   help = 'Expires IP->Hostname mappings from the ipmeta table'
   def handle(self, *args, **options):
         # http://stackoverflow.com/questions/1313120/retrieving-the-last-record-in-each-group
         for hnr in HostnameRule.objects.raw("select m1.* from openipmap_hostnamerule m1 LEFT JOIN openipmap_hostnamerule m2 ON (m1.hostname = m2.hostname and m1.id < m2.id ) WHERE m2.id IS NULL"):
            hostname = hnr.hostname
         #   SELECT m1.*
         #   FROM messages m1 LEFT JOIN messages m2
         #    ON (m1.name = m2.name AND m1.id < m2.id)
         #    WHERE m2.id IS NULL;
            ipm_list= IPMeta.objects.filter(invalidated=None, hostname=hostname).order_by('last_updated')
            if len(ipm_list) > 0:
                ipm = ipm_list[0]
                print "%s,%s,%s,\"%s\",%s" % ( ipm.ip, hnr.lat, hnr.lon, hnr.canonical_georesult, hostname )
         return
         now = datetime.now(pytz.utc)
         ips = set()
         current_ip = None
         ipm_list = []
         for ipm in IPMeta.objects.filter(invalidated=None).order_by('ip'):
            if current_ip == None:
               current_ip = ipm.ip
            if current_ip == ipm.ip: ## add it to ipm_list
               ipm_list.append( ipm )
               continue
            else:
               ## check validity for this IP and update if needed
               check_and_expire( current_ip , ipm_list )
               # reset
               ipm_list = [ipm]
               current_ip = ipm.ip
         check_and_expire( current_ip, ipm_list )      
