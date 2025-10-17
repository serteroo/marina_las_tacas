from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission, User
from accounts.models import Organization, UserProfile

class Command(BaseCommand):
    help = "Crea organización, grupos y vincula permisos mínimos"

    def handle(self, *args, **kwargs):
        org, _ = Organization.objects.get_or_create(name="Marina Las Tacas")

        # Grupos
        sup, _ = Group.objects.get_or_create(name="Supervisor")
        sec, _ = Group.objects.get_or_create(name="Secretaria")
        soc, _ = Group.objects.get_or_create(name="Socio")

        # (Permisos finos los afinamos luego según modelos)
        # p = Permission.objects.filter(codename__in=[...]); sup.permissions.add(*p)

        self.stdout.write(self.style.SUCCESS("Organización y grupos creados."))

        # Si quieres crear un usuario demo:
        if not User.objects.filter(username="supervisor").exists():
            u = User.objects.create_user("supervisor", email="sup@example.com", password="Passw0rd!")
            UserProfile.objects.create(user=u, organization=org, rut="12.345.678-5", telefono="+56911111111")
            u.groups.add(sup)
            self.stdout.write(self.style.SUCCESS("Usuario supervisor demo creado (Passw0rd!)."))
