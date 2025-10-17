from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db.models import Q
from accounts.models import UserProfile

User = get_user_model()

class UsernameEmailRutBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            user = User.objects.get(
                Q(username__iexact=username) | Q(email__iexact=username) |
                Q(userprofile__rut__iexact=username)
            )
        except User.DoesNotExist:
            return None
        if user.check_password(password):
            return user
        return None
