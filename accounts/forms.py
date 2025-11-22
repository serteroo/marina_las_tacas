from django import forms
from django.utils import timezone
import re

from .models import ContratoExterno, Applicant
from .validators import validar_rut_formato


# --- Helpers RUT ---
def normalizar_rut(raw: str) -> str:
    """Deja solo dígitos y K (mayúscula), sin puntos ni guión."""
    return re.sub(r"[^0-9K]", "", (raw or "").strip().upper())

def formatear_rut(cuerpo: str, dv: str) -> str:
    """Devuelve xx.xxx.xxx-x desde cuerpo+dv."""
    partes = []
    while len(cuerpo) > 3:
        partes.insert(0, cuerpo[-3:])
        cuerpo = cuerpo[:-3]
    if cuerpo:
        partes.insert(0, cuerpo)
    return f"{'.'.join(partes)}-{dv}"


# ---------------- Contrato Externo ----------------
class ContratoExternoForm(forms.ModelForm):
    class Meta:
        model = ContratoExterno
        exclude = ["organization", "estado", "supervisor"]
        widgets = {
            "rut": forms.TextInput(attrs={
                "inputmode": "numeric",
                "autocomplete": "off",
                "placeholder": "12.345.678-9",
                "maxlength": "12",
            }),
            "fecha_inicio": forms.DateInput(attrs={"type": "date"}),
            "fecha_fin": forms.DateInput(attrs={"type": "date"}),
            "licencia_vencimiento": forms.DateInput(attrs={"type": "date"}),
            "observaciones": forms.Textarea(attrs={"rows": 3}),
        }
        labels = {
            "nombre": "Nombre",
            "apellido": "Apellido",
            "rut": "RUT",
            "licencia_numero": "N° licencia",
            "licencia_vencimiento": "Vence licencia",
            "licencia_validada": "Licencia validada",
            "tipo_artefacto": "Tipo de embarcación",
            "detalle_artefacto": "Detalle de embarcación",
            "fecha_inicio": "Fecha inicio",
            "fecha_fin": "Fecha fin",
        }

    # Autocorrige y valida RUT (acepta 123456789 o 12.345.678-9)
    def clean_rut(self):
        raw = self.cleaned_data.get("rut", "")
        s = normalizar_rut(raw)                  # -> 123456789 o 12345678K
        if not re.match(r"^[0-9]{7,8}[0-9K]$", s):
            raise forms.ValidationError("RUT inválido.")
        cuerpo, dv = s[:-1], s[-1]
        rut_fmt = formatear_rut(cuerpo, dv)      # -> 12.345.678-9
        validar_rut_formato(rut_fmt)             # DV correcto, formato ok
        return rut_fmt

    def clean_licencia_vencimiento(self):
        fv = self.cleaned_data.get("licencia_vencimiento")
        if not fv:
            return fv
        if fv <= timezone.localdate():
            raise forms.ValidationError("Licencia vencida: no se permite el arriendo.")
        return fv

    def clean(self):
        cleaned = super().clean()
        fi, ff = cleaned.get("fecha_inicio"), cleaned.get("fecha_fin")
        if fi and ff and ff < fi:
            self.add_error("fecha_fin", "La fecha de término no puede ser anterior al inicio.")
        return cleaned


# ---------------- Registro Público (Applicant) ----------------
class PublicRegisterForm(forms.ModelForm):
    class Meta:
        model = Applicant
        fields = [
            "nombre", "apellido", "rut", "direccion",
            "email", "telefono",
            "numero_licencia", "vencimiento_licencia",
        ]
        labels = {
            "numero_licencia": "Número de licencia",
            "vencimiento_licencia": "Vencimiento licencia",
        }
        error_messages = {
            "email": {"unique": "Ya existe un solicitante con este email."},
            "rut":   {"unique": "Ya existe un solicitante con este RUT."},
        }
        widgets = {
            "rut": forms.TextInput(attrs={
                "inputmode": "numeric",
                "autocomplete": "off",
                "placeholder": "12.345.678-9",
                "maxlength": "12",
            }),
            "vencimiento_licencia": forms.DateInput(attrs={"type": "date"}),
        }

    def clean_rut(self):
        raw = self.cleaned_data.get("rut", "")
        s = normalizar_rut(raw)
        if not re.match(r"^[0-9]{7,8}[0-9K]$", s):
            raise forms.ValidationError("RUT inválido.")
        cuerpo, dv = s[:-1], s[-1]
        rut_fmt = formatear_rut(cuerpo, dv)
        validar_rut_formato(rut_fmt)
        return rut_fmt

    def clean_vencimiento_licencia(self):
        v = self.cleaned_data.get("vencimiento_licencia")
        if not v:
            return v
        if v <= timezone.localdate():
            raise forms.ValidationError("Licencia vencida.")
        return v
