from django.urls import path
from . import views

urlpatterns = [
    path("healthz/", views.healthz, name="healthz"),
    path("bloqueo/toggle/", views.toggle_bloqueo, name="toggle_bloqueo"),
    # Zarpe v1
    path("zarpe/solicitar/<int:emb_id>/", views.solicitar_zarpe, name="solicitar_zarpe"),
    path("zarpe/aprobar/<int:mov_id>/", views.aprobar_zarpe, name="aprobar_zarpe"),
    path("zarpe/salida/<int:mov_id>/", views.marcar_salida, name="marcar_salida"),
    path("zarpe/arribo/<int:mov_id>/", views.marcar_arribo, name="marcar_arribo"),
]

