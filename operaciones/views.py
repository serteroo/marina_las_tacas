# operaciones/views.py
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import redirect, get_object_or_404, render
from django.utils import timezone
from django.contrib.auth.decorators import login_required, user_passes_test
from accounts.models import UserProfile
from .models import Embarcacion, Movimiento, BloqueoClima
from accounts.views import is_supervisor

def healthz(request): return HttpResponse("ok")

@login_required
@user_passes_test(is_supervisor)
def toggle_bloqueo(request):
    prof = UserProfile.objects.get(user=request.user)
    obj, _ = BloqueoClima.objects.get_or_create(organization=prof.organization, defaults={"creado_por": prof})
    obj.is_blocked = not obj.is_blocked
    obj.motivo = request.POST.get("motivo","")
    obj.override_por = prof if not obj.is_blocked else None
    obj.save()
    return redirect("dashboard_supervisor")

# --- Zarpe v1 ---

@login_required
def solicitar_zarpe(request, emb_id):
    prof = UserProfile.objects.get(user=request.user)
    emb = get_object_or_404(Embarcacion, id=emb_id, organization=prof.organization)

    # si hay bloqueo clima y NO es supervisor, no permite
    bloqueo = BloqueoClima.objects.filter(organization=prof.organization, is_blocked=True).first()
    if bloqueo and not is_supervisor(request.user):
        return HttpResponseForbidden("Bloqueo por clima activo.")

    mov = Movimiento.objects.create(
        organization=prof.organization,
        socio=prof,
        embarcacion=emb,
        estado="SOLICITADO",
    )
    return redirect("dashboard_supervisor")  # luego haremos páginas dedicadas

@login_required
@user_passes_test(is_supervisor)
def aprobar_zarpe(request, mov_id):
    prof = UserProfile.objects.get(user=request.user)
    mov = get_object_or_404(Movimiento, id=mov_id, organization=prof.organization)
    mov.estado = "APROBADO"
    # ETA y tolerancia simples por ahora (1h + 15m). Luego lo hacemos editable.
    mov.eta = timezone.now() + timezone.timedelta(hours=1)
    mov.tolerancia_min = 15
    mov.save()
    return redirect("dashboard_supervisor")

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
    return redirect("dashboard_supervisor")

@login_required
def marcar_arribo(request, mov_id):
    prof = UserProfile.objects.get(user=request.user)
    mov = get_object_or_404(Movimiento, id=mov_id, organization=prof.organization)
    if mov.socio != prof and not is_supervisor(request.user):
        return HttpResponseForbidden("No autorizado.")
    mov.estado = "CERRADO"
    mov.hora_arribo = timezone.now()
    mov.save()
    return redirect("dashboard_supervisor")

