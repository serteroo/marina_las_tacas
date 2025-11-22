from django.conf import settings
from django.db import models
from django.core.validators import EmailValidator, MinValueValidator
from .validators import validar_rut_formato
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model
from .validators import validate_image_size, validate_image_content_type
import uuid
import os


def avatar_upload_to(instance, filename):
    ext = filename.split(".")[-1].lower()
    new_name = f"{uuid.uuid4().hex}.{ext}"
    return os.path.join("avatares", new_name)


class Organization(models.Model):
    name = models.CharField(max_length=150, unique=True)
    def __str__(self): return self.name

class UserProfile(models.Model):
    foto = models.ImageField(
        upload_to=avatar_upload_to,
        blank=True,
        null=True,
        validators=[validate_image_size, validate_image_content_type],
    )
    last_username_change = models.DateTimeField(blank=True, null=True)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT)

    rut = models.CharField(max_length=12, unique=True, null=True, blank=True)
    telefono = models.CharField(max_length=20, unique=True, null=True, blank=True)

    # NUEVO: control de clave
    must_change_password = models.BooleanField(default=True)

    mfa_enabled = models.BooleanField(default=True)
    mfa_method = models.CharField(
        max_length=10,
        choices=[("email","Email"),("sms","SMS"),("both","Ambos")],
        default="email"
    )

class MFAChallenge(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    code = models.CharField(max_length=6)
    channel = models.CharField(max_length=10, choices=[("email","Email"),("sms","SMS")])
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

class ContratoExterno(models.Model):
    TIPO_ARTEFACTO = [
        ("BOTE", "Bote"),
        ("LANCHA", "Lancha"),
        ("MOTO_AGUA", "Moto de agua"),
        ("OTRO", "Otro"),
    ]
    ESTADOS = [
        ("PENDIENTE", "Pendiente"),
        ("APROBADO",  "Aprobado"),
        ("RECHAZADO", "Rechazado"),
    ]

    # --- Organización (con metadata completa) ---
    organization = models.ForeignKey(
        "accounts.Organization",            # mantiene compatibilidad con apps
        on_delete=models.SET_NULL,          # permite null
        null=True, blank=True,
        related_name="contratos_externos",
        verbose_name="Organización",
    )

    # --- Solicitante (union de ambos) ---
    nombre   = models.CharField("Nombre", max_length=80)
    apellido = models.CharField("Apellido", max_length=80)
    # conserva el validador de RUT y permite longitudes de ambos modelos
    rut      = models.CharField("RUT", max_length=20, validators=[validar_rut_formato])

    # EmailField ya valida, pero conservamos el EmailValidator explícito
    email    = models.EmailField("Email", validators=[EmailValidator()])

    # el mayor de los dos max_length (30) para no perder nada
    telefono = models.CharField("Teléfono", max_length=30, blank=True)

    # campos presentes en el primer modelo
    direccion = models.CharField("Dirección", max_length=200, blank=True, default="")
    firma     = models.ImageField(upload_to="firmas/", null=True, blank=True)

    # --- Licencia (union) ---
    licencia_numero      = models.CharField(max_length=50, blank=True)
    licencia_vencimiento = models.DateField(null=True, blank=True)
    licencia_validada    = models.BooleanField(
        default=False,
        help_text="Marcar cuando el supervisor confirma que la licencia es válida",
    )

    # --- Artefacto (del segundo + safe defaults) ---
    tipo_artefacto = models.CharField(
        "Tipo de embarcación",
        max_length=20,
        choices=TIPO_ARTEFACTO,
        blank=True,
        null=True,
        default="OTRO",
    )
    detalle_artefacto = models.CharField(
        "Detalle de embarcación", max_length=150, blank=True, default=""
    )

    # --- Vigencia arriendo (del segundo) ---
    fecha_inicio = models.DateField("Fecha inicio", null=True, blank=True)
    fecha_fin    = models.DateField("Fecha fin",    null=True, blank=True)

    # --- Gestión/estado (del segundo) ---
    documento     = models.FileField("Documento", upload_to="contratos/", blank=True, null=True)
    estado        = models.CharField("Estado", max_length=10, choices=ESTADOS, default="PENDIENTE")
    supervisor    = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="contratos_externos_gestionados",
        verbose_name="Supervisor",
    )
    observaciones = models.TextField("Observaciones", blank=True)

    # --- Timestamps (ambos tenían creado_en; aquí también dejamos actualizado_en) ---
    creado_en      = models.DateTimeField("Creado en", auto_now_add=True)
    actualizado_en = models.DateTimeField("Actualizado en", auto_now=True)

    class Meta:
        ordering = ["-creado_en"]
        verbose_name = "Contrato externo"
        verbose_name_plural = "Contratos externos"

    def __str__(self):
        # usa display del tipo y estado legible
        tipo = self.get_tipo_artefacto_display() if self.tipo_artefacto else "—"
        return f"{self.apellido}, {self.nombre} • {tipo} • {self.estado}"

    @property
    def licencia_vencida(self):
        if not self.licencia_vencimiento:
            return True
        return self.licencia_vencimiento < timezone.localdate()

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.fecha_fin and self.fecha_inicio and self.fecha_fin < self.fecha_inicio:
            raise ValidationError("La fecha de término no puede ser anterior al inicio.")

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

User = get_user_model()

class LoginAttempt(models.Model):
    username = models.CharField(max_length=150)
    ip_address = models.GenericIPAddressField()
    timestamp = models.DateTimeField(auto_now_add=True)
    successful = models.BooleanField(default=False)

    def __str__(self):
        status = "OK" if self.successful else "FAIL"
        return f"{self.timestamp} {self.ip_address} {self.username} {status}"
    

User = get_user_model()

class AuditLog(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=100)
    object_type = models.CharField(max_length=50)
    object_id = models.CharField(max_length=50)
    details = models.JSONField(blank=True, null=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"[{self.timestamp}] {self.user} {self.action} {self.object_type}#{self.object_id}"



