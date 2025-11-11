# accounts/middleware.py
from django.shortcuts import redirect
from django.urls import resolve

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

        prof = getattr(user, "profile", None)
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
