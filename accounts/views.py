import random, datetime
from django.utils import timezone
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required, permission_required, user_passes_test
from django.core.mail import send_mail
from django.contrib import messages
from .models import MFAChallenge, UserProfile, Organization, ContratoExterno
from .forms import ContratoExternoForm
from operaciones.models import Movimiento, BloqueoClima
from datetime import timedelta 
from operaciones.models import Embarcacion, Movimiento, BloqueoClima
from django.conf import settings

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
            # perfil
            try:
                profile = UserProfile.objects.get(user=user)
            except UserProfile.DoesNotExist:
                messages.warning(request, "No existe perfil de usuario. Contacta al administrador.")
                return render(request, "registration/login.html")

            # backend usado (necesario para luego hacer login con 2FA)
            backend = getattr(user, "backend", None) or settings.AUTHENTICATION_BACKENDS[0]

            if profile.mfa_enabled:
                if not user.email:
                    messages.warning(request, "Tu usuario no tiene email configurado. Se omitirá MFA por ahora.")
                    login(request, user, backend=backend)
                    return redirect("dashboard")

                # genera desafío MFA y guarda datos en sesión
                code = f"{random.randint(0, 999999):06d}"
                exp = timezone.now() + datetime.timedelta(minutes=5)
                MFAChallenge.objects.create(user=user, code=code, channel="email", expires_at=exp)

                _send_mfa_email(user, code)

                request.session["pending_user_id"] = user.id
                request.session["pending_auth_backend"] = backend

                messages.info(request, "Te enviamos un código de verificación al correo.")
                return redirect("two_factor")

            # Sin MFA -> entra directo
            login(request, user, backend=backend)
            return redirect("dashboard")

        messages.error(request, "Credenciales inválidas.")
    return render(request, "registration/login.html") 

def two_factor_view(request):
    pending_id = request.session.get("pending_user_id")
    if not pending_id:
        return redirect("login")

    if request.method == "POST":
        code = request.POST.get("code", "").strip()

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

        # marcar usado
        ch.used = True
        ch.save()

        # loguear con el backend correcto
        user = get_user_model().objects.get(id=pending_id)
        backend = request.session.pop("pending_auth_backend", None) or settings.AUTHENTICATION_BACKENDS[0]
        login(request, user, backend=backend)

        # limpiar sesión temporal
        request.session.pop("pending_user_id", None)

        return redirect("dashboard")

    return render(request, "registration/two_factor.html")

def logout_view(request):
    logout(request)
    return redirect("login")

@login_required
def dashboard(request):
    if is_supervisor(request.user):
        return redirect("dashboard_supervisor")
    return redirect("dashboard_socio")


@login_required
def contrato_externo_new(request):
    prof = UserProfile.objects.get(user=request.user)
    org = prof.organization
    if request.method == "POST":
        form = ContratoExternoForm(request.POST, request.FILES)
        if form.is_valid():
            contrato = form.save(commit=False)
            contrato.organization = org
            contrato.licencia_validada = False
            contrato.save()
            messages.success(request, "Contrato ingresado. Pendiente de validación de licencia.")
            return redirect("dashboard_supervisor")
    else:
        form = ContratoExternoForm()
    return render(request, "accounts/contrato_externo_form.html", {"form": form})

def is_supervisor(user):
    return user.groups.filter(name__in=["Supervisor","Secretaria"]).exists() or user.is_superuser

@login_required
@user_passes_test(is_supervisor)
def dashboard_supervisor(request):
    prof = UserProfile.objects.get(user=request.user)
    org = prof.organization

    # Conteos y últimos
    ctx = {
        "total_solicitados":  Movimiento.objects.filter(organization=org, estado="SOLICITADO").count(),
        "total_aprobados":    Movimiento.objects.filter(organization=org, estado="APROBADO").count(),
        "en_salida":          Movimiento.objects.filter(organization=org, estado="EN_SALIDA").count(),
        "pendientes_arribo":  Movimiento.objects.filter(organization=org, estado__in=["EN_SALIDA","EN_ARRIBO"]).count(),
        "ultimos":            Movimiento.objects.filter(organization=org).order_by("-id")[:10],
        "bloqueo":            BloqueoClima.objects.filter(organization=org).first(),
    }

    # ⚠︎ Atrasados: ETA + tolerancia < ahora y sin arribo
    atrasados = []
    qs = Movimiento.objects.filter(
        organization=org,
        hora_arribo__isnull=True,
        eta__isnull=False,
    )
    ahora = timezone.now()
    for m in qs:
        if (m.eta + timedelta(minutes=(m.tolerancia_min or 0))) < ahora:
            atrasados.append(m.id)

    ctx["atrasados"] = set(atrasados)
    return render(request, "dashboard/supervisor.html", ctx)

@login_required
def dashboard_socio(request):
    prof = UserProfile.objects.get(user=request.user)
    org = prof.organization

    embarcaciones = Embarcacion.objects.filter(organization=org, propietario=prof)
    movimientos   = Movimiento.objects.filter(organization=org, socio=prof).order_by("-id")[:10]
    bloqueo       = BloqueoClima.objects.filter(organization=org).first()

    return render(request, "dashboard/socio.html", {
        "mis_embarcaciones": embarcaciones,
        "mis_movimientos": movimientos,
        "bloqueo": bloqueo,
    })


