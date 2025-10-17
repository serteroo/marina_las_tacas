from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import redirect
from accounts.models import UserProfile
from .models import BloqueoClima
from accounts.views import is_supervisor

@login_required
@user_passes_test(is_supervisor)
def toggle_bloqueo(request):
    prof = UserProfile.objects.get(user=request.user)
    obj, _ = BloqueoClima.objects.get_or_create(organization=prof.organization, defaults={"creado_por": prof})
    obj.is_blocked = not obj.is_blocked
    obj.motivo = request.POST.get("motivo","")
    obj.override_por = prof if obj.is_blocked is False else None
    obj.save()
    return redirect("dashboard_supervisor")
