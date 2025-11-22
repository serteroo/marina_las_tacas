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
from accounts.roles import is_supervisor, is_supervisor_strict, is_secretaria, is_socio, menu_kind_for
from accounts.security import audit

def healthz(request): return HttpResponse("ok")


@login_required
@user_passes_test(is_supervisor)
def toggle_bloqueo(request):
    prof = UserProfile.objects.get(user=request.user)
    obj, _ = BloqueoClima.objects.get_or_create(
        organization=prof.organization,
        defaults={"creado_por": prof}
    )
    obj.is_blocked = not obj.is_blocked
    obj.motivo = request.POST.get("motivo", "")
    obj.override_por = prof if not obj.is_blocked else None
    obj.save()

    audit(
        request.user,
        action="toggle_bloqueo_clima",
        obj=obj,
        details={"is_blocked": obj.is_blocked, "motivo": obj.motivo},
    )

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
    prof = UserProfile.objects.select_related("organization").get(user=request.user)
    org = prof.organization

    mov = get_object_or_404(
        Movimiento.objects.select_related("socio__user", "embarcacion"),
        id=mov_id,
        organization=org,   # <<< amarra a la org del supervisor
    )

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

@login_required
@user_passes_test(is_supervisor)
def movimiento_revisar(request, pk):
    prof = UserProfile.objects.select_related("organization").get(user=request.user)
    org = prof.organization

    mov = get_object_or_404(Movimiento, pk=pk, organization=org)

    # Si no está SOLICITADO, no tiene sentido “revisar”
    if mov.estado != "SOLICITADO":
        messages.info(request, f"El movimiento ya está {mov.get_estado_display().lower()}.")
        return redirect("accounts:dashboard_supervisor")

    return render(request, "operaciones/movimiento_revisar.html", {"mov": mov})

@login_required
def mis_zarpes(request):
    prof = UserProfile.objects.select_related("organization").get(user=request.user)
    org = prof.organization

    ESTADOS = ["SOLICITADO", "APROBADO", "EN_SALIDA", "EN_ARRIBO", "CERRADO", "RECHAZADO"]

    estado = request.GET.get("estado", "")
    try:
        lim = int(request.GET.get("lim", "50"))
    except ValueError:
        lim = 50
    lim = max(1, min(lim, 200))

    qs = (
        Movimiento.objects
        .filter(organization=org, socio=prof)    # <<< org + socio
        .select_related("embarcacion")
        .order_by("-id")
    )

    if estado in ESTADOS:
        qs = qs.filter(estado=estado)

    ctx = {
        "active_nav": "mis_zarpes",
        "movs": qs[:lim],
        "estados": ESTADOS,
        "estado": estado,
        "lim": lim,
    }
    return render(request, "operaciones/mis_zarpes.html", ctx)

