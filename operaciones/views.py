from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import redirect, get_object_or_404, render
from django.utils import timezone
from django.contrib.auth.decorators import login_required, user_passes_test
from accounts.models import UserProfile, ContratoExterno
from .models import Embarcacion, Movimiento, BloqueoClima
from accounts.views import is_supervisor
from .forms import AprobarZarpeForm
from .forms import SolicitarZarpeForm
from django.contrib import messages

def healthz(request): return HttpResponse("ok")

def is_supervisor(user):
    return user.groups.filter(name__in=["Supervisor","Secretaria"]).exists() or user.is_superuser

@login_required
@user_passes_test(is_supervisor)
def toggle_bloqueo(request):
    prof = UserProfile.objects.get(user=request.user)
    obj, _ = BloqueoClima.objects.get_or_create(organization=prof.organization, defaults={"creado_por": prof})
    obj.is_blocked = not obj.is_blocked
    obj.motivo = request.POST.get("motivo","")
    obj.override_por = prof if not obj.is_blocked else None
    obj.save()
    if (
        request.user.is_superuser
        or request.user.groups.filter(name__in=["Supervisor", "Secretaría"]).exists()
    ):
        return redirect("accounts:dashboard_supervisor")



# --- Zarpe v1 ---

@login_required
def solicitar_zarpe(request, emb_id):
    prof = UserProfile.objects.select_related("organization").get(user=request.user)
    embarcacion = get_object_or_404(Embarcacion, id=emb_id, propietario=prof)

    # BLOQUEO POR CLIMA: guardia de seguridad (servidor)
    if BloqueoClima.objects.filter(organization=prof.organization, is_blocked=True).exists():
        b = (BloqueoClima.objects
             .filter(organization=prof.organization, is_blocked=True)
             .order_by("-created_at", "-id").first())
        messages.error(request, f"Zarpe bloqueado por clima. Motivo: {b.motivo if b and b.motivo else 'N/A'}")
        return redirect("dashboard_socio")

    if request.method == "POST":
        form = SolicitarZarpeForm(request.POST)
        if form.is_valid():
            m = form.save(commit=False)
            m.organization = prof.organization
            m.socio = prof
            m.embarcacion = embarcacion
            m.estado = "SOLICITADO"
            m.save()
            messages.success(request, "Solicitud de zarpe enviada.")
            return redirect("accounts:dashboard_socio")   # <--- CON NAMESPACE
    else:
        form = SolicitarZarpeForm()

    return render(request, "operaciones/solicitar_zarpe.html", {
        "form": form,
        "embarcacion": embarcacion,
    })

@login_required
@user_passes_test(is_supervisor)
def aprobar_zarpe(request, mov_id):
    mov = get_object_or_404(Movimiento.objects.select_related("socio__user","embarcacion"), id=mov_id)

    if request.method == "POST":
        if "aprobar" in request.POST:
            mov.estado = "APROBADO"
            mov.hora_salida = timezone.now()
            mov.save()
            messages.success(request, "Zarpe aprobado.")
        elif "rechazar" in request.POST:
            mov.estado = "RECHAZADO"
            mov.save()
            messages.warning(request, "Solicitud rechazada.")
        return redirect("accounts:dashboard_supervisor")

    # GET: muestra ficha con datos
    return render(request, "operaciones/aprobar_zarpe.html", {"mov": mov})


@login_required
def marcar_salida(request, mov_id):
    prof = UserProfile.objects.get(user=request.user)
    mov = get_object_or_404(Movimiento, id=mov_id, organization=prof.organization)

    # Solo el socio dueño del movimiento o supervisor
    if mov.socio != prof and not is_supervisor(request.user):
        return HttpResponseForbidden("No autorizado.")

    mov.estado = "EN_SALIDA"
    mov.hora_salida = timezone.now()
    if not mov.eta:
        mov.eta = mov.hora_salida + timezone.timedelta(hours=1)
    mov.save()
    return redirect("accounts:dashboard_supervisor")

@login_required
def marcar_arribo(request, mov_id):
    prof = UserProfile.objects.get(user=request.user)
    mov = get_object_or_404(Movimiento, id=mov_id, organization=prof.organization)
    if mov.socio != prof and not is_supervisor(request.user):
        return HttpResponseForbidden("No autorizado.")
    mov.estado = "CERRADO"
    mov.hora_arribo = timezone.now()
    mov.save()
    return redirect("accounts:dashboard_supervisor")

