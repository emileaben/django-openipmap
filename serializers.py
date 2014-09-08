from rest_framework import serializers
from openipmap.models import *

class UserField(serializers.RelatedField):
    def to_native(self, value):
        return "%s %s <%s>" % (value.first_name,value.last_name,value.id)

class DomainRegexRuleSerializer(serializers.ModelSerializer):
    #user=UserField()
    class Meta:
        model = DomainRegexRule
        fields = ('domain','regex','georesult','confidence','user')

class MyDomainRegexRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = DomainRegexRule
        fields = ('domain','regex','georesult','confidence')

class IPRuleSerializer(serializers.ModelSerializer):
    #ip = serializers.ModelField(
    #    model_field=IPRule()._meta.get_field('ip'),
    #    validators=[]
    #)
    class Meta:
        model = IPRule
        fields = ('ip','created','georesult','confidence','user','lat','lon','canonical_georesult')
        read_only_fields = fields

class MyIPRuleSerializer(serializers.ModelSerializer):
    ## validation doesn't work for forms it seems, so need to go through some hoops
    ### for 'ip' to work
    #ip = serializers.ModelField(
    #    model_field=IPRule()._meta.get_field('ip'),
    #    validators=[]
    #)
    class Meta:
        model = IPRule
        fields = ('ip','created','georesult','confidence','canonical_georesult','lat','lon')
        read_only_fields = ('canonical_georesult','lat','lon')

class HostnameRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = HostnameRule
        fields = ('hostname','created','georesult','canonical_georesult','lat','lon','confidence','user')
        read_only_fields = fields

class MyHostnameRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = HostnameRule
        fields = ('hostname','created','georesult','canonical_georesult','lat','lon','confidence')
        read_only_fields = ('canonical_georesult','lat','lon')
