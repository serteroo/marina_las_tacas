# operaciones/admin.py
from django.contrib import admin
from .models import Embarcacion, Amarra, Movimiento, BloqueoClima, Auditoria

@admin.register(Embarcacion)
class EmbarcacionAdmin(admin.ModelAdmin):
    list_display  = ("matricula", "tipo", "organization", "propietario")
    list_filter   = ("organization", "tipo")
    search_fields = ("matricula",)

    def save_model(self, request, obj, form, change):
        # SI hay propietario, fuerza que la organización coincida
        if obj.propietario:
            obj.organization = obj.propietario.organization
        super().save_model(request, obj, form, change)

admin.site.register(Amarra)
admin.site.register(Movimiento)
admin.site.register(BloqueoClima)
admin.site.register(Auditoria)


