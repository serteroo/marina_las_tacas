# accounts/urls.py
from django.urls import path, reverse_lazy
from django.contrib.auth import views as auth_views
from . import views
from .views import CambioClaveInicialView, contrato_externo_aprobar, contrato_externo_detail, contrato_externo_new, contrato_externo_rechazar
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

    path("contratos/externos/nuevo/", contrato_externo_new, name="contrato_externo_new"),
    path("contratos/externos/<int:pk>/", contrato_externo_detail, name="contrato_externo_detail"),
    path("contratos/externos/<int:pk>/aprobar/", contrato_externo_aprobar, name="contrato_externo_aprobar"),
    path("contratos/externos/<int:pk>/rechazar/", contrato_externo_rechazar, name="contrato_externo_rechazar"),

    path(
        "password/reset/",
        auth_views.PasswordResetView.as_view(
            template_name="registration/password_reset_form.html",
            email_template_name="registration/password_reset_email.txt",
            subject_template_name="registration/password_reset_subject.txt",
            success_url=reverse_lazy("accounts:password_reset_done"),
        ),
        name="password_reset",
    ),
    path(
        "password/reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="registration/password_reset_done.html"
        ),
        name="password_reset_done",
    ),
    path(
        "password/reset/confirm/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="registration/password_reset_confirm.html",
            success_url=reverse_lazy("accounts:password_reset_complete"),
        ),
        name="password_reset_confirm",
    ),
    path(
        "password/reset/complete/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="registration/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),

    path("perfil/", views.perfil, name="perfil"),
    path("perfil/editar/", views.perfil_editar, name="perfil_editar"),
    path("perfil/cambiar-usuario/", views.perfil_cambiar_usuario, name="perfil_cambiar_usuario"),
    path("mis-embarcaciones/", views.mis_embarcaciones, name="mis_embarcaciones"),
    path("super/socios/", views.super_socios, name="super_socios"),
    path("super/socios/", views.socios_list, name="socios_list"),
    path("super/embarcaciones/", views.embarcaciones_list, name="embarcaciones_list"),
    path("super/socios/export/xlsx/", views.socios_export_xlsx, name="socios_export_xlsx"),
    path("super/contratos/", views.contratos_list, name="contratos_list"),
    path("super/contratos/export/xlsx/", views.contratos_export_xlsx, name="contratos_export_xlsx"),


]
