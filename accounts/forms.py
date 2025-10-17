from django import forms
from .models import ContratoExterno
from .validators import validar_rut_formato
from datetime import date

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
