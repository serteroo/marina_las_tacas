import random, datetime
from django.utils import timezone
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, permission_required, user_passes_test
from django.core.mail import send_mail
from django.contrib import messages
from .models import MFAChallenge, UserProfile, Organization, ContratoExterno
from .forms import ContratoExternoForm
from operaciones.models import Movimiento, BloqueoClima

def _send_mfa_email(user, code):
    send_mail(
        subject="Tu código de verificación",
        message=f"Tu código es: {code}",
        from_email=None, recipient_list=[user.email], fail_silently=False
    )

def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)
        if user:
            # Obtén el perfil (con la señal post_save ya no debería faltar)
            try:
                profile = UserProfile.objects.get(user=user)
            except UserProfile.DoesNotExist:
                messages.warning(request, "No existe perfil de usuario. Contacta al administrador.")
                return render(request, "registration/login.html")

            # Si MFA está habilitado, exige email; si no hay email, entra pero avisa
            if profile.mfa_enabled:
                if not user.email:
                    messages.warning(request, "Tu usuario no tiene email configurado. Se omitirá MFA por ahora.")
                    login(request, user)
                    return redirect("dashboard")

                # Genera y envía código MFA por email
                code = f"{random.randint(0, 999999):06d}"
                exp = timezone.now() + datetime.timedelta(minutes=5)
                MFAChallenge.objects.create(user=user, code=code, channel="email", expires_at=exp)
                from django.core.mail import send_mail
                send_mail("Tu código de verificación", f"Tu código es: {code}", None, [user.email], fail_silently=False)
                request.session["pending_user_id"] = user.id
                messages.info(request, "Te enviamos un código de verificación al correo.")
                return redirect("two_factor")

            # Sin MFA → entrar directo
            login(request, user)
            return redirect("dashboard")
        messages.error(request, "Credenciales inválidas.")
    return render(request, "registration/login.html")

def two_factor_view(request):
    pending_id = request.session.get("pending_user_id")
    if not pending_id:
        return redirect("login")
    if request.method == "POST":
        code = request.POST.get("code","").strip()
        try:
            ch = MFAChallenge.objects.filter(user_id=pending_id, used=False).latest("created_at")
        except MFAChallenge.DoesNotExist:
            messages.error(request, "No hay desafío activo. Inicia sesión nuevamente.")
            return redirect("login")
        if ch.expires_at < timezone.now():
            messages.error(request, "Código expirado. Inicia sesión otra vez.")
            return redirect("login")
        if ch.code != code:
            messages.error(request, "Código incorrecto.")
            return render(request, "registration/two_factor.html")
        ch.used = True; ch.save()
        from django.contrib.auth import get_user_model
        user = get_user_model().objects.get(id=pending_id)
        del request.session["pending_user_id"]
        login(request, user)
        return redirect("dashboard")
    return render(request, "registration/two_factor.html")

def logout_view(request):
    logout(request)
    return redirect("login")

@login_required
def dashboard(request):
    # Placeholder por rol (Supervisor/Secretaría/Socio). Luego lo separamos.
    return render(request, "dashboard/index.html", {})

@login_required
def contrato_externo_new(request):
    org = Organization.objects.get(name="Mrina Las Tacas")
    if request.method == "POST":
        form = ContratoExternoForm(request.POST, request.FILES)
        if form.is_valid():
            contrato = form.save(commit=False)
            contrato.organization = org
            # por defecto NO validada la licencia hasta que supervisor revise:
            contrato.licencia_validada = False
            contrato.save()
            from django.contrib import messages
            messages.success(request, "Contrato ingresado. Pendiente de validación de licencia.")
            return redirect("dashboard")
    else:
        form = ContratoExternoForm()
    return render(request, "accounts/contrato_externo_form.html", {"form": form})

def is_supervisor(user):
    return user.groups.filter(name__in=["Supervisor","Secretaria"]).exists() or user.is_superuser

@login_required
@user_passes_test(is_supervisor)
def dashboard_supervisor(request):
    ctx = {
        "total_solicitados": Movimiento.objects.filter(estado="SOLICITADO").count(),
        "total_aprobados": Movimiento.objects.filter(estado="APROBADO").count(),
        "en_salida": Movimiento.objects.filter(estado="EN_SALIDA").count(),
        "pendientes_arribo": Movimiento.objects.filter(estado__in=["EN_SALIDA","EN_ARRIBO"]).count(),
        "ultimos": Movimiento.objects.order_by("-id")[:10],
        "bloqueo": BloqueoClima.objects.first(),
    }
    return render(request, "dashboard/supervisor.html", ctx)