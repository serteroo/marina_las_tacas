# accounts/urls.py
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from .views import CambioClaveInicialView
from django.contrib.auth.views import PasswordChangeDoneView

app_name = "accounts"

urlpatterns = [
    # Login / Logout
    path("ingresar/", views.login_view, name="login"),
    path("salir/", views.logout_view, name="logout"),

    # 2FA
    path("seguridad/codigo/", views.two_factor_view, name="two_factor"),
    path("seguridad/codigo/reenviar/", views.two_factor_resend, name="two_factor_resend"),

    # Dashboards
    path("", views.dashboard, name="dashboard"),
    path("panel/supervisor/", views.dashboard_supervisor, name="dashboard_supervisor"),
    path("dashboard/supervisor/", views.dashboard_supervisor, name="dashboard_supervisor"),  # alias
    path("panel/socio/", views.dashboard_socio, name="dashboard_socio"),
    path("dashboard/socio/", views.dashboard_socio, name="dashboard_socio"),  # alias

    # Registro público
    path("registrarse/", views.public_register, name="public_register"),

    # Revisión de postulantes (supervisor)
    path("revision/", views.review_list, name="review_list"),
    path("revision/<int:pk>/aprobar/", views.approve_applicant, name="approve_applicant"),
    path("revision/<int:pk>/rechazar/", views.reject_applicant, name="reject_applicant"),

    # Cambio de contraseña forzado tras 2FA (primera vez)
    path("seguridad/cambiar-clave/", CambioClaveInicialView.as_view(), name="password_change"),
    path(
        "seguridad/cambiar-clave/listo/",
        PasswordChangeDoneView.as_view(template_name="registration/password_change_done.html"),
        name="password_change_done",
    ),
]
