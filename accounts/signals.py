from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import UserProfile, Organization

@receiver(post_save, sender=User)
def ensure_profile(sender, instance, created, **kwargs):
    if not created:
        return
    org, _ = Organization.objects.get_or_create(name="Marina Las Tacas")
    # sin rut/telefono por defecto (son únicos)
    UserProfile.objects.create(user=instance, organization=org)


