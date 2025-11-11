from django import forms
from .models import ContratoExterno, Applicant
from .validators import validar_rut_formato
from datetime import date
import re

class ContratoExternoForm(forms.ModelForm):
    class Meta:
        model = ContratoExterno
        fields = ["nombre","apellido","rut","licencia_numero","licencia_vencimiento",
                  "direccion","telefono","email","firma"]
    def clean_rut(self):
        rut = self.cleaned_data["rut"]
        validar_rut_formato(rut); return rut
    def clean_licencia_vencimiento(self):
        fv = self.cleaned_data["licencia_vencimiento"]
        if fv <= date.today():
            raise forms.ValidationError("Licencia vencida: no se permite el arriendo.")
        return fv

def normalizar_rut(raw: str) -> str:
    return (raw or '').strip().upper().replace('.', '').replace('-', '')

def formatear_rut(cuerpo: str, dv: str) -> str:
    # Formatea desde la derecha: 12.345.678-5
    partes = []
    while len(cuerpo) > 3:
        partes.insert(0, cuerpo[-3:])
        cuerpo = cuerpo[:-3]
    if cuerpo:
        partes.insert(0, cuerpo)
    return f"{'.'.join(partes)}-{dv}"

class PublicRegisterForm(forms.ModelForm):
    class Meta:
        model = Applicant
        fields = [
            "nombre", "apellido", "rut", "direccion",
            "email", "telefono",
            "numero_licencia", "vencimiento_licencia",  # <- usa los nombres REALES del modelo
        ]
        labels = {
            "numero_licencia": "Número de licencia",
            "vencimiento_licencia": "Vencimiento licencia",
        }
        error_messages = {
            "email": {"unique": "Ya existe un solicitante con este email."},
            "rut":   {"unique": "Ya existe un solicitante con este RUT."},
        }
        widgets = {'vencimiento_licencia': forms.DateInput(attrs={'type':'date'})}

    def clean_rut(self):
        raw = self.cleaned_data.get('rut', '')
        norm = normalizar_rut(raw)           # ej: 12345678K
        if not re.match(r'^\d{7,8}[0-9K]$', norm):
            raise forms.ValidationError("RUT inválido.")
        # Reusa tu validador (acepta con puntos/guion; le pasamos formateado)
        cuerpo, dv = norm[:-1], norm[-1]
        rut_formateado = formatear_rut(cuerpo, dv)
        validar_rut_formato(rut_formateado)  # ← si DV no cuadra, lanzará ValidationError
        return rut_formateado