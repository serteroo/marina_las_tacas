from django.contrib.auth import get_user_model

User = get_user_model()

SUPERVISOR_GROUP = "Supervisor"
SECRETARIA_GROUP = "Secretaria"
SOCIO_GROUP = "Socio"

def is_supervisor(user) -> bool:
    """Supervisor + Secretaria + superuser (rol 'alto mando')."""
    return (
        getattr(user, "is_authenticated", False)
        and (
            user.is_superuser
            or user.groups.filter(name__in=[SUPERVISOR_GROUP, SECRETARIA_GROUP]).exists()
        )
    )

def is_supervisor_strict(user) -> bool:
    """Solo grupo Supervisor (para acciones críticas futuras)."""
    return (
        getattr(user, "is_authenticated", False)
        and user.groups.filter(name=SUPERVISOR_GROUP).exists()
    )

def is_secretaria(user) -> bool:
    return (
        getattr(user, "is_authenticated", False)
        and user.groups.filter(name=SECRETARIA_GROUP).exists()
    )

def is_socio(user) -> bool:
    """Socio que NO es del 'alto mando'."""
    return (
        getattr(user, "is_authenticated", False)
        and user.groups.filter(name=SOCIO_GROUP).exists()
        and not is_supervisor(user)
    )

def menu_kind_for(user) -> str:
    """Devuelve 'super' (Supervisor/Secretaria/superuser) o 'user' (Socio)."""
    return "super" if is_supervisor(user) else "user"
