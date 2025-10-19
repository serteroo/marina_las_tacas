from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import redirect, get_object_or_404, render
from django.utils import timezone
from django.contrib.auth.decorators import login_required, user_passes_test
from accounts.models import UserProfile, ContratoExterno
from .models import Embarcacion, Movimiento, BloqueoClima
from accounts.views import is_supervisor
from .forms import AprobarZarpeForm
from .forms import SolicitarZarpeForm
from django.utils import timezone

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

    # Debe ser el propietario
    if emb.propietario_id != prof.id and not is_supervisor(request.user):
        return HttpResponseForbidden("No puedes solicitar zarpe para esta embarcación.")

    # Bloqueo clima (solo supervisor puede saltarlo)
    bloqueo = BloqueoClima.objects.filter(organization=prof.organization, is_blocked=True).first()
    if bloqueo and not is_supervisor(request.user):
        return HttpResponseForbidden("Bloqueo por clima activo.")

    # Externo sin licencia válida: bloqueo total
    es_externo = getattr(prof, "es_externo", False)
    if es_externo and not is_supervisor(request.user):
        hoy = timezone.now().date()
        ok = ContratoExterno.objects.filter(
            organization=prof.organization, email=request.user.email,
            licencia_validada=True, licencia_vencimiento__gt=hoy
        ).exists()
        if not ok:
            return HttpResponseForbidden("Externo sin licencia válida o vencida.")

    if request.method == "POST":
        form = SolicitarZarpeForm(request.POST)
        if form.is_valid():
            mov = Movimiento.objects.create(
                organization=prof.organization,
                socio=prof,
                embarcacion=emb,
                estado="SOLICITADO",
                pasajeros=form.cleaned_data["pasajeros"],
                destino=form.cleaned_data.get("destino") or "",
                nota=form.cleaned_data.get("nota") or "",
                eta=form.cleaned_data.get("eta_sugerida"),  # supervisor puede ajustar al aprobar
            )
            # feedback simple
            return redirect("dashboard_socio" if not is_supervisor(request.user) else "dashboard_supervisor")
    else:
        form = SolicitarZarpeForm()

    return render(request, "operaciones/solicitar_zarpe.html", {"form": form, "emb": emb})

@login_required
@user_passes_test(is_supervisor)
def aprobar_zarpe(request, mov_id):
    prof = UserProfile.objects.get(user=request.user)
    mov = get_object_or_404(Movimiento, id=mov_id, organization=prof.organization)

    if request.method == "POST":
        form = AprobarZarpeForm(request.POST)
        if form.is_valid():
            mov.estado = "APROBADO"
            mov.eta = form.cleaned_data["eta"]
            mov.tolerancia_min = form.cleaned_data["tolerancia_min"]
            # si aún no tiene hora_salida, la calculará al marcar salida
            mov.save()
            return redirect("dashboard_supervisor")
    else:
        # ETA sugerida +1h
        sugerida = timezone.now() + timezone.timedelta(hours=1)
        # Para widget datetime-local: to naive ISO sin TZ (simple rápido)
        inicial = sugerida.strftime("%Y-%m-%dT%H:%M")
        form = AprobarZarpeForm(initial={"eta": inicial, "tolerancia_min": 15})

    return render(request, "operaciones/aprobar_zarpe.html", {"form": form, "mov": mov})

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

