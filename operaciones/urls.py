from django.urls import path
from . import views

urlpatterns = [
    path("bloqueo/toggle/", views.toggle_bloqueo, name="toggle_bloqueo"),
]
