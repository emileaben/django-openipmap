#!/usr/bin/env python
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User

MAX_USER_ID=1000

class Command(BaseCommand):
   args = ''
   help = 'Create mock users, passwd=vagrant username=user%d'
   def handle(self, *args, **options):
      current_max_user = User.objects.latest('id')
      current_max_id = current_max_user.id
      if current_max_id >= MAX_USER_ID:
         return
      for uid in range( current_max_id + 1, MAX_USER_ID + 1 ):
         try:
            new_username = "_tmp_user%d" % ( uid )
            u = User.objects.create_user( new_username, password='vagrant')
            u.save() 
            u.username = "user%d" % ( u.id )
            u.save()
         except:
            pass
