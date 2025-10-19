from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.mail import send_mail
from accounts.models import Organization
from operaciones.models import Movimiento

class Command(BaseCommand):
    help = "Genera reporte de los últimos 3h (salidas, arribos, atrasos) por organización."

    def handle(self, *args, **kwargs):
        ahora = timezone.now()
        desde = ahora - timezone.timedelta(hours=3)
        for org in Organization.objects.all():
            qs = Movimiento.objects.filter(organization=org)
            salidas = qs.filter(hora_salida__gte=desde, hora_salida__lte=ahora).count()
            arribos = qs.filter(hora_arribo__gte=desde, hora_arribo__lte=ahora).count()

            # Atrasados: ETA + tolerancia < ahora y sin arribo
            atrasados = qs.filter(
                eta__isnull=False,
                hora_arribo__isnull=True
            )
            total_atrasados = sum(
                1 for m in atrasados
                if (m.eta + timezone.timedelta(minutes=m.tolerancia_min)) < ahora
            )

            resumen = (
                f"[{org.name}] Últimas 3 horas\n"
                f"- Salidas: {salidas}\n"
                f"- Arribos: {arribos}\n"
                f"- Atrasados: {total_atrasados}\n"
            )

            # En dev: a consola y a email backend de consola
            self.stdout.write(self.style.SUCCESS(resumen))
            try:
                send_mail(
                    subject=f"Reporte 3h — {org.name}",
                    message=resumen,
                    from_email=None,
                    recipient_list=["supervisor@example.com"],
                    fail_silently=True,
                )
            except Exception:
                pass
