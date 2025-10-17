from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User

from accounts.models import Organization, UserProfile

@receiver(post_save, sender=User)
def ensure_profile(sender, instance, created, **kwargs):
    # Garantiza que siempre exista la organización y el perfil
    org, _ = Organization.objects.get_or_create(name="Marina Las Tacas")
    UserProfile.objects.get_or_create(
        user=instance,
        defaults={"organization": org, "rut": "11.111.111-1", "telefono": "+56900000000"}
    )
