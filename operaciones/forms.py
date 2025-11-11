from django import forms
from django.utils import timezone
from .models import Movimiento, Embarcacion

class AprobarZarpeForm(forms.Form):
    eta = forms.DateTimeField(
        label="ETA (hora estimada de arribo)",
        widget=forms.DateTimeInput(attrs={"type":"datetime-local"}),
    )
    tolerancia_min = forms.IntegerField(min_value=0, initial=15, label="Tolerancia (min)")

    def clean_eta(self):
        eta = self.cleaned_data["eta"]
        # asume TZ-aware; si no, puedes ajustar a timezone.make_aware
        if eta <= timezone.now():
            raise forms.ValidationError("La ETA debe ser a futuro.")
        return eta

class SolicitarZarpeForm(forms.ModelForm):
    class Meta:
        model = Movimiento
        fields = ["pasajeros", "destino", "eta", "tolerancia_min", "nota"]
        widgets = {
            "eta": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }
        labels = {
            "eta": "ETA (hora estimada de arribo)",
            "tolerancia_min": "Tolerancia (min)",
        }