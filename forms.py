from django import forms

class ContributionUploadForm(forms.Form):
    file  = forms.FileField()

#class DomainRegexRuleForm(forms.ModelForm):
#    class Meta:
#        model = DomainRegexRule
#        exclude = ['created','updated','user','deleted']
