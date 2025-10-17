from django.contrib import admin
from .models import Amarra, Embarcacion, Movimiento, BloqueoClima, Auditoria
admin.site.register(Amarra)
admin.site.register(Embarcacion)
admin.site.register(Movimiento)
admin.site.register(BloqueoClima)
admin.site.register(Auditoria)
