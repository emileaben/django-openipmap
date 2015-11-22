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

class Command(BaseCommand):
   args = ''
   help = 'Export ip->loc mappings'
   def handle(self, *args, **options):
         # http://stackoverflow.com/questions/1313120/retrieving-the-last-record-in-each-group
         for hnr in HostnameRule.objects.raw("select m1.* from openipmap_hostnamerule m1 LEFT JOIN openipmap_hostnamerule m2 ON (m1.hostname = m2.hostname and m1.id < m2.id ) WHERE m2.id IS NULL"):
            hostname = hnr.hostname
            ipm_list= IPMeta.objects.filter(invalidated=None, hostname=hostname).order_by('last_updated')
            if len(ipm_list) > 0:
                ipm = ipm_list[0]
                print "%s,%s,%s,\"%s\",%s,%s,%s" % ( ipm.ip, hnr.lat, hnr.lon, hnr.canonical_georesult, hostname, hnr.created, hnr.user_id )
