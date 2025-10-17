from django.contrib import admin
from .models import Organization, UserProfile, MFAChallenge, ContratoExterno
admin.site.register(Organization)
admin.site.register(UserProfile)
admin.site.register(MFAChallenge)
admin.site.register(ContratoExterno)
