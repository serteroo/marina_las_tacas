from django.urls import path
from . import views

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("2fa/", views.two_factor_view, name="two_factor"),
    path("", views.dashboard, name="dashboard"),
    path("contratos/externo/nuevo/", views.contrato_externo_new, name="contrato_externo_new"),
    path("dashboard/supervisor/", views.dashboard_supervisor, name="dashboard_supervisor"),
 
]
