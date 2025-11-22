from datetime import timedelta
from django.utils import timezone
from .models import LoginAttempt, AuditLog
from django.db import models 

MAX_FAILS = 5
WINDOW_MINUTES = 20

def get_client_ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        # primer IP de la cadena
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")

def is_login_blocked(username: str, ip_address: str) -> bool:
    now = timezone.now()
    window_start = now - timedelta(minutes=WINDOW_MINUTES)

    fails = LoginAttempt.objects.filter(
        timestamp__gte=window_start,
        successful=False,
    ).filter(
        models.Q(username=username) | models.Q(ip_address=ip_address)
    ).count()

    return fails >= MAX_FAILS

def register_login_attempt(username: str, ip_address: str, success: bool):
    LoginAttempt.objects.create(
        username=username or "",
        ip_address=ip_address,
        successful=success,
    )

def audit(user, action: str, obj, details: dict | None = None):
    AuditLog.objects.create(
        user=user if user.is_authenticated else None,
        action=action,
        object_type=obj.__class__.__name__,
        object_id=str(getattr(obj, "pk", "")),
        details=details or {},
    )