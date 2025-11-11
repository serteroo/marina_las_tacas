import random, datetime
from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required, permission_required, user_passes_test
from django.core.mail import send_mail
from django.contrib import messages
from .models import MFAChallenge, UserProfile, Organization, ContratoExterno
from .forms import ContratoExternoForm
from datetime import timedelta 
from operaciones.models import Embarcacion, Movimiento, BloqueoClima
from django.conf import settings
from django.views.decorators.cache import never_cache
from django.utils.decorators import method_decorator
from django.contrib.auth.models import User, Group
from django.contrib.auth.hashers import make_password
from .forms import PublicRegisterForm
from .models import Applicant, Profile
import secrets
from django.contrib.auth.views import PasswordChangeView, PasswordChangeDoneView
from django.urls import reverse_lazy, reverse
from django.apps import apps
from django.utils.crypto import get_random_string
from django.db import transaction


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
                    return redirect("accounts:dashboard")

                # genera desafío MFA y guarda datos en sesión
                code = f"{random.randint(0, 999999):06d}"
                exp = timezone.now() + datetime.timedelta(minutes=5)
                MFAChallenge.objects.create(user=user, code=code, channel="email", expires_at=exp)

                _send_mfa_email(user, code)

                request.session["pending_user_id"] = user.id
                request.session["pending_auth_backend"] = backend

                messages.info(request, "Te enviamos un código de verificación al correo.")
                return redirect("accounts:two_factor")

            # Sin MFA -> entra directo
            login(request, user, backend=backend)
            return redirect("accounts:dashboard")

        messages.error(request, "Credenciales inválidas.")
    return render(request, "registration/login.html") 

def logout_view(request):
    logout(request)
    return redirect("accounts:login")  # si usas namespace "accounts"

RESEND_COOLDOWN_SECONDS = 30

def _seconds_to_resend(user_id: int) -> int:
    """Devuelve cuantos segundos faltan para poder reenviar (0 si ya se puede)."""
    last = (MFAChallenge.objects
            .filter(user_id=user_id, used=False)
            .order_by("-created_at")
            .first())
    if not last:
        return 0
    elapsed = (timezone.now() - last.created_at).total_seconds()
    remaining = RESEND_COOLDOWN_SECONDS - int(elapsed)
    return remaining if remaining > 0 else 0


def two_factor_view(request):
    pending_id = request.session.get("pending_user_id")
    if not pending_id:
        messages.info(request, "Sesión 2FA no encontrada. Inicia sesión nuevamente.")
        return redirect("accounts:login")

    if request.method == "POST":
        code = request.POST.get("code", "").strip()

        try:
            ch = (MFAChallenge.objects
                  .filter(user_id=pending_id, used=False)
                  .latest("created_at"))
        except MFAChallenge.DoesNotExist:
            messages.error(request, "No hay desafío activo. Inicia sesión nuevamente.")
            return redirect("accounts:login")

        if ch.expires_at < timezone.now():
            messages.error(request, "Código expirado. Inicia sesión otra vez.")
            return redirect("accounts:login")

        if ch.code != code:
            messages.error(request, "Código incorrecto.")
            # volvemos a pintar, pero enviando los segundos restantes de cooldown
            return render(request, "registration/two_factor.html", {
                "resend_seconds": _seconds_to_resend(pending_id),
            })

        ch.used = True
        ch.save(update_fields=["used"])

        UserModel = get_user_model()
        user = UserModel.objects.get(id=pending_id)
        backend = request.session.pop("pending_auth_backend", None) or settings.AUTHENTICATION_BACKENDS[0]
        login(request, user, backend=backend)
        request.session.pop("pending_user_id", None)

        if hasattr(user, "profile") and getattr(user.profile, "must_change_password", False):
            return redirect("accounts:password_change")

        return redirect("accounts:dashboard")

    # GET
    return render(request, "registration/two_factor.html", {
        "resend_seconds": _seconds_to_resend(pending_id),
    })


def two_factor_resend(request):
    """Reenvía el código si pasó el cooldown."""
    pending_id = request.session.get("pending_user_id")
    if not pending_id:
        messages.info(request, "Sesión 2FA no encontrada. Inicia sesión nuevamente.")
        return redirect("accounts:login")

    remaining = _seconds_to_resend(pending_id)
    if remaining > 0:
        messages.info(request, f"Podrás reenviar en {remaining}s.")
        return redirect("accounts:two_factor")

    # Generar y enviar nuevo código
    UserModel = get_user_model()
    user = UserModel.objects.get(id=pending_id)

    code = f"{random.randint(0, 999999):06d}"
    exp = timezone.now() + timedelta(minutes=5)
    MFAChallenge.objects.create(user=user, code=code, channel="email", expires_at=exp)
    _send_mfa_email(user, code)

    messages.success(request, "Te enviamos un nuevo código a tu correo.")
    return redirect("accounts:two_factor")

@login_required
def dashboard(request):
    if is_supervisor(request.user):
        return redirect("accounts:dashboard_supervisor")
    return redirect("accounts:dashboard_socio")


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
            return redirect("accounts:dashboard_supervisor")
    else:
        form = ContratoExternoForm()
    return render(request, "accounts/contrato_externo_form.html", {"form": form})

def is_supervisor(user):
    return user.groups.filter(name__in=["Supervisor","Secretaria"]).exists() or user.is_superuser

@login_required
@user_passes_test(is_supervisor)
def dashboard_supervisor(request):
    prof = UserProfile.objects.select_related("organization").get(user=request.user)
    org = prof.organization

    Applicant = apps.get_model('accounts', 'Applicant')
    pend_aplicants_qs = Applicant.objects.filter(estado='pending')

    ctx = {
        "total_solicitados":  Movimiento.objects.filter(organization=org, estado="SOLICITADO").count(),
        "total_aprobados":   Movimiento.objects.filter(organization=org, estado="APROBADO").count(),
        "en_salida":         Movimiento.objects.filter(organization=org, estado="EN_SALIDA").count(),
        "pendientes_arribo": Movimiento.objects.filter(organization=org, estado__in=["EN_SALIDA","EN_ARRIBO"]).count(),
        "ultimos":           Movimiento.objects.filter(organization=org)
                              .select_related("embarcacion","socio__user").order_by("-id")[:10],
        "bloqueo":           BloqueoClima.objects.filter(organization=org).order_by("-created_at","-id").first(),
        "pendientes":        Movimiento.objects.filter(organization=org, estado="SOLICITADO")
                              .select_related("embarcacion","socio__user").order_by("id"),
        # solo el número:
        "postulantes_pendientes_count": pend_aplicants_qs.count(),
    }
    return render(request, "dashboard/supervisor.html", ctx)

@never_cache
@login_required
def dashboard_socio(request):
    # 1) perfil del usuario logueado
    prof = UserProfile.objects.select_related("organization").get(user=request.user)

    # 2) embarcaciones del socio (clave)
    embarcaciones = (
        Embarcacion.objects
        .filter(propietario=prof)
        .select_related("amarra", "organization", "propietario")
        .order_by("matricula")
    )

    # 3) últimos movimientos del socio
    ultimos = (
        Movimiento.objects
        .filter(socio=prof)
        .select_related("embarcacion")
        .order_by("-id")[:10]
    )

    # 4) bloqueo por clima de su organización
    bloqueo = (
        BloqueoClima.objects
        .filter(organization=prof.organization, is_blocked=True)
        .order_by("-created_at", "-id")
        .first()
    )

    return render(request, "dashboard/socio.html", {
        "embarcaciones": embarcaciones,
        "ultimos": ultimos,
        "bloqueo": bloqueo,
    })


def public_register(request):
    if request.method == 'POST':
        form = PublicRegisterForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "¡Gracias! Tu solicitud quedó en revisión. Te avisaremos por correo.")
            return redirect('accounts:login')
    else:
        form = PublicRegisterForm()
    return render(request, 'accounts/public_register.html', {'form': form})

@login_required
@permission_required('accounts.view_applicant', raise_exception=True)
def review_list(request):
    Applicant = apps.get_model('accounts','Applicant')
    postulantes = Applicant.objects.filter(estado='pending').order_by('-created_at')
    return render(request, 'accounts/review_list.html', {'postulantes': postulantes})

@login_required
@permission_required('accounts.change_applicant', raise_exception=True)
def approve_applicant(request, pk):
    if request.method != 'POST':
        return redirect('accounts:review_list')

    Applicant = apps.get_model('accounts', 'Applicant')
    Profile   = apps.get_model('accounts', 'Profile')

    a = get_object_or_404(Applicant, pk=pk)

    # Ya procesada
    if a.estado != 'pending':
        messages.info(request, "Esta postulación ya fue procesada.")
        return redirect('accounts:review_list')

    # Validación robusta de licencia
    lic  = (a.numero_licencia or '').strip()
    venc = a.vencimiento_licencia  # DateField o None
    if not lic or venc is None:
        messages.error(request, "Faltan datos de licencia (número o vencimiento).")
        return redirect('accounts:review_list')

    # Crear/actualizar Usuario
    username = (a.email or a.rut).strip().lower()
    temp_password = get_random_string(10)

    User = get_user_model()
    user, _ = User.objects.get_or_create(
        username=username,
        defaults={
            'email': a.email,
            'first_name': a.nombre,
            'last_name': a.apellido,
        }
    )
    # Sincroniza datos básicos y clave temporal
    user.set_password(temp_password)
    user.email = a.email
    user.first_name = a.nombre
    user.last_name  = a.apellido
    user.save()

    # Organización vía UserProfile
    reviewer_prof = UserProfile.objects.select_related('organization').get(user=request.user)
    up, _ = UserProfile.objects.get_or_create(
        user=user,
        defaults={'organization': reviewer_prof.organization}
    )
    if up.organization_id != reviewer_prof.organization_id:
        up.organization = reviewer_prof.organization
        up.save(update_fields=['organization'])

    # Forzar cambio de clave y **poblar campos NOT NULL** del Profile
    # (numero_licencia y vencimiento_licencia)
    Profile.objects.update_or_create(
        user=user,
        defaults={
            'must_change_password': True,
            'numero_licencia': lic,
            'vencimiento_licencia': venc,
        }
    )

    # Agregar al grupo "Socio" si existe
    try:
        socio = Group.objects.get(name='Socio')
        user.groups.add(socio)
    except Group.DoesNotExist:
        pass

    # Marcar Applicant aprobado
    a.estado = 'approved'
    a.reviewed_by = request.user
    a.reviewed_at = timezone.now()
    a.save(update_fields=['estado', 'reviewed_by', 'reviewed_at'])

    # Envío de correo (en local saldrá por consola si usas EMAIL_BACKEND de consola)
    try:
        login_url = request.build_absolute_uri(reverse('accounts:login'))
        cuerpo = (
            f"Hola {a.nombre},\n\n"
            f"Tu solicitud fue aprobada.\n\n"
            f"Usuario: {user.username}\n"
            f"Contraseña temporal: {temp_password}\n\n"
            f"Por seguridad, cambia la contraseña al iniciar sesión.\n"
            f"Ingresar: {login_url}\n"
        )
        send_mail("Tu acceso al Club Náutico", cuerpo, None, [a.email], fail_silently=False)
    except Exception:
        # No detenemos el flujo si falla el envío
        pass

    messages.success(request, f"{a.nombre} aprobado.")
    return redirect('accounts:review_list')


@login_required
@permission_required('accounts.change_applicant', raise_exception=True)
def reject_applicant(request, pk):
    if request.method != 'POST':
        return redirect('accounts:review_list')

    Applicant = apps.get_model('accounts', 'Applicant')
    a = get_object_or_404(Applicant, pk=pk)

    if a.estado != 'pending':
        messages.info(request, "Esta postulación ya fue procesada.")
        return redirect('accounts:review_list')

    motivo = (request.POST.get('motivo') or '').strip()

    a.estado = 'rejected'
    a.motivo_revision = motivo
    a.reviewed_by = request.user
    a.reviewed_at = timezone.now()
    a.save(update_fields=['estado', 'motivo_revision', 'reviewed_by', 'reviewed_at'])

    # (Opcional) Notificar por correo al solicitante que fue rechazado
    try:
        cuerpo = (
            f"Hola {a.nombre},\n\n"
            f"Tu solicitud fue rechazada.\n"
            f"{'Motivo: ' + motivo if motivo else ''}\n"
        )
        send_mail("Actualización de solicitud", cuerpo, None, [a.email], fail_silently=True)
    except Exception:
        pass

    messages.warning(request, f"{a.nombre} rechazado.")
    return redirect('accounts:review_list')

class CambiarPasswordView(PasswordChangeView):
    template_name = 'registration/password_change_form.html'
    success_url = reverse_lazy('accounts:password_change_done')

    def form_valid(self, form):
        response = super().form_valid(form)
        # Aquí marcamos que ya no es obligatorio cambiarla
        if hasattr(self.request.user, 'profile') and self.request.user.profile.must_change_password:
            self.request.user.profile.must_change_password = False
            self.request.user.profile.save(update_fields=['must_change_password'])
        return response

class CambioClaveInicialView(PasswordChangeView):
    template_name = 'registration/password_change_form.html'   # <<< nuestro HTML simple
    success_url = reverse_lazy('accounts:dashboard')            # tras guardar, va al dashboard

    def form_valid(self, form):
        resp = super().form_valid(form)
        # bajar el flag para que el middleware no vuelva a forzar cambio
        if hasattr(self.request.user, 'profile'):
            self.request.user.profile.must_change_password = False
            self.request.user.profile.save(update_fields=['must_change_password'])
        return resp


