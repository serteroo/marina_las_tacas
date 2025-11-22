import re
from django.core.exceptions import ValidationError

MAX_IMAGE_SIZE_MB = 5
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}

RUT_REGEX = r"^\d{1,2}\.\d{3}\.\d{3}-[\dkK]$"


def validar_rut_formato(rut:str):
    if not re.match(RUT_REGEX, rut):
        raise ValidationError("RUT inválido. Formato esperado: xx.xxx.xxx-x")
    # Verificador
    cuerpo, dv = rut.replace(".","").split("-")
    s = 0
    m = 2
    for c in reversed(cuerpo):
        s += int(c)*m
        m = 2 if m==7 else m+1
    resto = 11 - (s % 11)
    dv_calc = "0" if resto==11 else "K" if resto==10 else str(resto)
    if dv.upper() != dv_calc:
        raise ValidationError("RUT con dígito verificador incorrecto.")

def validar_password_fuerte(pw:str):
    if len(pw) < 8: raise ValidationError("Mínimo 8 caracteres.")
    if not re.search(r"[A-Z]", pw): raise ValidationError("Debe incluir una mayúscula.")
    if not re.search(r"[a-z]", pw): raise ValidationError("Debe incluir una minúscula.")
    if not re.search(r"\d", pw): raise ValidationError("Debe incluir un dígito.")
    if not re.search(r"[^A-Za-z0-9]", pw): raise ValidationError("Debe incluir un carácter especial.")

def validate_image_size(image):
    if image.size > MAX_IMAGE_SIZE_MB * 1024 * 1024:
        raise ValidationError(f"La imagen no puede superar los {MAX_IMAGE_SIZE_MB} MB.")

def validate_image_content_type(image):
    content_type = getattr(image, "content_type", None)
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise ValidationError("Formato de imagen no permitido. Usa JPG, PNG o WEBP.")
