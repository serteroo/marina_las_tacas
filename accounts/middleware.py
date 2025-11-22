# accounts/middleware.py
from django.shortcuts import redirect
from django.urls import resolve
import re
from django.contrib import messages
from django.contrib.auth import logout
from django.shortcuts import redirect

# Vistas permitidas cuando el usuario debe cambiar su contraseña (con namespace)
ALLOWED_VIEW_NAMES = {
    "accounts:login",               # /accounts/ingresar/   (ajusta al tuyo)
    "accounts:logout",              # /accounts/salir/
    "accounts:two_factor",          # /accounts/two-factor/
    "accounts:two_factor_resend",   # /accounts/two-factor/resend/  <-- OJO: coma
    "accounts:password_change",     # /accounts/seguridad/cambiar-clave/
    "accounts:password_change_done",# /accounts/seguridad/cambiar-clave/listo/
    "accounts:public_register",     # /accounts/registrarse/
}

class MustChangePasswordMiddleware:
    """
    Si el usuario autenticado tiene profile.must_change_password = True,
    solo le permitimos acceder a las vistas whitelisteadas. En cualquier
    otro caso lo redirigimos a cambiar su contraseña.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Deja pasar estáticos y media
        p = request.path
        if p.startswith("/static/") or p.startswith("/media/"):
            return self.get_response(request)

        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return self.get_response(request)

        # Usamos UserProfile como fuente de verdad
        prof = getattr(user, "userprofile", None)
        if not prof or not getattr(prof, "must_change_password", False):
            return self.get_response(request)


        # Resolvemos nombre de la vista actual (namespaced)
        try:
            view_name = resolve(request.path_info).view_name
        except Exception:
            view_name = None

        # Si no está permitido, redirigimos al cambio de clave (namespaced)
        if view_name not in ALLOWED_VIEW_NAMES:
            return redirect("accounts:password_change")

        return self.get_response(request)
    
ROLE_ROUTE_RULES = [
    # Supervisor / Secretaria (alto mando)
    (
        re.compile(r"^/accounts/(panel|dashboard)/supervisor/?$"),
        {"groups": {"Supervisor", "Secretaria"}, "superuser_ok": True},
    ),
    # Socio
    (
        re.compile(r"^/accounts/(panel|dashboard)/socio/?$"),
        {"groups": {"Socio"}, "superuser_ok": True},
    ),
]

class RoleRouteGuardMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path

        if request.user.is_authenticated:
            # 1) Detecta cambio de dashboard -> cierra sesión
            if path.startswith("/accounts/dashboard/"):
                # extrae slug del dashboard de la URL
                slug = path.rstrip("/").split("/")[-1]  # 'supervisor' o 'socio'
                current = request.session.get("active_dashboard")
                if current and current != slug:
                    logout(request)
                    messages.info(request, "Sesión cerrada por cambio de contexto.")
                    return redirect("accounts:login")

            # 2) Reglas de acceso por ruta/rol
            for regex, rule in ROLE_ROUTE_RULES:
                if regex.match(path):
                    if rule.get("superuser_ok", True) and request.user.is_superuser:
                        break
                    required = rule["groups"]
                    if not request.user.groups.filter(name__in=required).exists():
                        logout(request)
                        messages.warning(request, "Acceso no autorizado. Debes iniciar sesión nuevamente.")
                        return redirect("accounts:login")
                    break

        return self.get_response(request)
