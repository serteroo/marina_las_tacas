from django import forms
from django.utils import timezone

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
