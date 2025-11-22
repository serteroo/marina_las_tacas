# accounts/admin.py
from django.contrib import admin
from .models import Organization, UserProfile, MFAChallenge, ContratoExterno

@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display  = ("name",)
    search_fields = ("name",)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display  = ("user", "organization", "rut", "telefono", "mfa_enabled", "mfa_method")
    list_filter   = ("organization", "mfa_enabled", "mfa_method")
    search_fields = ("user__username", "user__email", "rut", "telefono")
    autocomplete_fields = ("user", "organization")


@admin.register(MFAChallenge)
class MFAChallengeAdmin(admin.ModelAdmin):
    list_display  = ("user", "channel", "code", "used", "expires_at", "created_at")
    list_filter   = ("channel", "used", "created_at")
    search_fields = ("user__username", "user__email", "code")
    readonly_fields = ("created_at",)


class ContratoExternoAdmin(admin.ModelAdmin):
    list_display = (
        "organization",
        "apellido", "nombre", "rut",
        "licencia_numero", "licencia_vencimiento", "licencia_validada",
        "tipo_artefacto", "detalle_artefacto",
        "estado", "creado_en",
    )
    list_filter = ("organization", "licencia_validada", "licencia_vencimiento", "estado", "creado_en")
    search_fields = ("rut", "apellido", "nombre", "licencia_numero", "telefono", "email")
    date_hierarchy = "licencia_vencimiento"
    readonly_fields = ("creado_en", "actualizado_en")
    ordering = ("-creado_en",)

    fieldsets = (
        ("Organización", {"fields": ("organization",)}),
        ("Solicitante", {"fields": (("nombre", "apellido"), "rut", ("email", "telefono"))}),
        ("Licencia", {"fields": (("licencia_numero", "licencia_vencimiento"), "licencia_validada")}),
        ("Embarcación y fechas", {"fields": (("tipo_artefacto", "detalle_artefacto"), ("fecha_inicio", "fecha_fin"))}),
        ("Gestión", {"fields": (("estado", "supervisor"), "observaciones", ("creado_en", "actualizado_en"))}),
    )


