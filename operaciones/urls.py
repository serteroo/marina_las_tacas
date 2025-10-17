from django.urls import path
from . import views

urlpatterns = [
    path("ping-operaciones/", views.ping, name="op_ping"),
]
