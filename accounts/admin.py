from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import UserProfile

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    extra = 0

class UserAdmin(BaseUserAdmin):
    inlines = [UserProfileInline]

    # clave: ocultar inline en la vista de "add"
    def get_inline_instances(self, request, obj=None):
        if obj is None:
            return []  # en add no mostramos inlines; la señal crea el perfil
        return super().get_inline_instances(request, obj)

admin.site.unregister(User)
admin.site.register(User, UserAdmin)

