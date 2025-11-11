from django.db import models
from accounts.models import Organization, UserProfile

class Amarra(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT)
    codigo = models.CharField(max_length=30, unique=True)
    estado = models.CharField(max_length=10, default="LIBRE")  # LIBRE/OCUPADA
    def __str__(self): return self.codigo

class Embarcacion(models.Model):
    TIPOS = [("LANCHA","Lancha"),("YATE","Yate"),("MOTO","Moto de agua")]
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT)
    matricula = models.CharField(max_length=30, unique=True)
    tipo = models.CharField(max_length=10, choices=TIPOS)
    propietario = models.ForeignKey(UserProfile, on_delete=models.PROTECT, related_name="embarcaciones")
    amarra = models.ForeignKey(Amarra, on_delete=models.SET_NULL, null=True, blank=True)
    foto = models.ImageField(upload_to="embarcaciones/", null=True, blank=True)
    def __str__(self): return f"{self.matricula} ({self.tipo})"

class Movimiento(models.Model):
    ESTADOS = [("SOLICITADO","Solicitado"),("APROBADO","Aprobado"),
               ("EN_SALIDA","En salida"),("EN_ARRIBO","En arribo"),("CERRADO","Cerrado")]
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT)
    socio = models.ForeignKey(UserProfile, on_delete=models.PROTECT)
    embarcacion = models.ForeignKey(Embarcacion, on_delete=models.PROTECT)
    estado = models.CharField(max_length=12, choices=ESTADOS, default="SOLICITADO")
    hora_salida = models.DateTimeField(null=True, blank=True)
    eta = models.DateTimeField(null=True, blank=True)
    tolerancia_min = models.PositiveIntegerField(default=0)
    hora_arribo = models.DateTimeField(null=True, blank=True)
    observaciones = models.TextField(blank=True)
    pasajeros = models.PositiveIntegerField(default=1)
    destino = models.CharField(max_length=120, blank=True)
    nota = models.CharField(max_length=240, blank=True)


    def __str__(self):
        return f"{self.embarcacion.matricula} - {self.estado}"

class BloqueoClima(models.Model):
    organization = models.OneToOneField(Organization, on_delete=models.CASCADE)
    is_blocked = models.BooleanField(default=False)
    motivo = models.CharField(max_length=200, blank=True)
    creado_por = models.ForeignKey(UserProfile, on_delete=models.PROTECT, related_name="+")
    override_por = models.ForeignKey(UserProfile, on_delete=models.PROTECT, null=True, blank=True, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

class Auditoria(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT)
    usuario = models.ForeignKey(UserProfile, on_delete=models.PROTECT)
    accion = models.CharField(max_length=50)  # APROBAR_ZARPE, ACTIVAR_BLOQUEO, OVERRIDE, etc.
    detalle = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

