from django.conf import settings
from django.db import models
from django.core.validators import EmailValidator
from .validators import validar_rut_formato



class Organization(models.Model):
    name = models.CharField(max_length=150, unique=True)
    def __str__(self): return self.name

class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT)
    rut = models.CharField(max_length=12, unique=True, null=True, blank=True)
    telefono = models.CharField(max_length=20, unique=True, null=True, blank=True)
    mfa_enabled = models.BooleanField(default=True)
    mfa_method = models.CharField(max_length=10, choices=[("email","Email"),("sms","SMS"),("both","Ambos")], default="email")
    def __str__(self): return f"{self.user.username} @ {self.organization.name}"

class MFAChallenge(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    code = models.CharField(max_length=6)
    channel = models.CharField(max_length=10, choices=[("email","Email"),("sms","SMS")])
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

class ContratoExterno(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT)
    nombre = models.CharField(max_length=80)
    apellido = models.CharField(max_length=80)
    rut = models.CharField(max_length=12, validators=[validar_rut_formato])
    licencia_numero = models.CharField(max_length=40)
    licencia_vencimiento = models.DateField()
    direccion = models.CharField(max_length=200)
    telefono = models.CharField(max_length=20)
    email = models.EmailField(validators=[EmailValidator()])
    firma = models.ImageField(upload_to="firmas/", null=True, blank=True)  # opcional por ahora
    licencia_validada = models.BooleanField(default=False)  # control de bloqueo total si False
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("rut","licencia_numero")]  # no duplicar contratos de la misma persona
    def __str__(self): return f"{self.rut} - {self.apellido}, {self.nombre}"

class Applicant(models.Model):
    STATUS = (('pending','Pendiente'),('approved','Aprobado'),('rejected','Rechazado'))
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    rut = models.CharField(max_length=12, unique=True, error_messages={"unique": "Ya existe un solicitante con este RUT."})
    direccion = models.CharField(max_length=200)
    email = models.EmailField(unique=True, error_messages={"unique": "Ya existe un solicitante con este email."})
    telefono = models.CharField(max_length=20)
    numero_licencia = models.CharField(max_length=30)
    vencimiento_licencia = models.DateField()
    estado = models.CharField(max_length=10, choices=STATUS, default='pending')
    motivo_revision = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='reviews')
    def __str__(self): return f"{self.nombre} {self.apellido} - {self.rut}"

class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    rut = models.CharField(max_length=12, unique=True)
    direccion = models.CharField(max_length=200)
    telefono = models.CharField(max_length=20)
    numero_licencia = models.CharField(max_length=30)
    vencimiento_licencia = models.DateField()
    must_change_password = models.BooleanField(default=True)
    es_socio = models.BooleanField(default=True)
    def __str__(self): return self.user.get_username()

