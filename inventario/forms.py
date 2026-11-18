"""
Formularios de la app.
Ciclo de vida: instanciación -> is_valid() -> [to_python, validators, clean_<campo>] -> clean() -> cleaned_data -> save()
"""
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import MensajeContacto, Producto
from .validators import sanitize_input, validar_sin_html, validar_sin_sql, validar_telefono

PALABRAS_PROHIBIDAS = {"spam", "gratis", "casino"}


# ---------------------------------------------------------------------------
# 1) Formulario CLÁSICO (forms.Form): no está ligado a un modelo
# ---------------------------------------------------------------------------
class ContactoForm(forms.Form):
    nombre = forms.CharField(max_length=100, min_length=3, validators=[validar_sin_html])
    email = forms.EmailField()
    confirmar_email = forms.EmailField(label="Confirmar email")
    telefono = forms.CharField(max_length=9, required=False, validators=[validar_telefono])
    asunto = forms.CharField(max_length=150, validators=[validar_sin_sql])
    mensaje = forms.CharField(widget=forms.Textarea(attrs={"rows": 4}), min_length=10)
    acepta_terminos = forms.BooleanField(label="Acepto la política de privacidad")

    # Nivel 1: validación por campo -------------------------------------
    def clean_nombre(self):
        nombre = sanitize_input(self.cleaned_data["nombre"])
        if any(ch.isdigit() for ch in nombre):
            raise forms.ValidationError("El nombre no debe contener números.")
        return nombre.title()

    def clean_email(self):
        return sanitize_input(self.cleaned_data["email"], minusculas=True)

    def clean_confirmar_email(self):
        return sanitize_input(self.cleaned_data["confirmar_email"], minusculas=True)

    def clean_mensaje(self):
        mensaje = sanitize_input(self.cleaned_data["mensaje"])
        encontradas = [p for p in PALABRAS_PROHIBIDAS if p in mensaje.lower()]
        if encontradas:
            raise forms.ValidationError(
                "El mensaje contiene palabras no permitidas: %(p)s", params={"p": ", ".join(encontradas)}
            )
        return mensaje

    # Nivel 2: validación cross-field (solo corre con los campos que pasaron) --
    def clean(self):
        cleaned = super().clean()
        email, confirmar = cleaned.get("email"), cleaned.get("confirmar_email")
        if email and confirmar and email != confirmar:
            # add_error: error asociado a un campo, no detiene las demás validaciones
            self.add_error("confirmar_email", "Los correos no coinciden.")
        asunto, mensaje = cleaned.get("asunto"), cleaned.get("mensaje")
        if asunto and mensaje and asunto.strip().lower() == mensaje.strip().lower():
            # ValidationError en clean() -> error global (__all__ / non_field_errors)
            raise forms.ValidationError("El asunto y el mensaje no pueden ser idénticos.")
        return cleaned

    def guardar(self, ip=None):
        d = self.cleaned_data
        return MensajeContacto.objects.create(
            nombre=d["nombre"], email=d["email"], asunto=sanitize_input(d["asunto"]),
            mensaje=d["mensaje"], ip=ip,
        )


# ---------------------------------------------------------------------------
# 2) ModelForm: genera campos y validación a partir del modelo Producto
# ---------------------------------------------------------------------------
class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = ["sku", "nombre", "categoria", "descripcion", "precio", "precio_oferta", "stock", "stock_minimo", "activo"]
        widgets = {
            "descripcion": forms.Textarea(attrs={"rows": 3}),
            "sku": forms.TextInput(attrs={"placeholder": "ABC-1234"}),
        }
        error_messages = {
            "sku": {"unique": "Ya existe un producto con ese SKU."},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["categoria"].queryset = self.fields["categoria"].queryset.filter(activa=True)

    def clean_sku(self):
        # Se normaliza a mayúsculas ANTES del validador de modelo
        return sanitize_input(self.cleaned_data["sku"]).upper()

    def clean_nombre(self):
        return sanitize_input(self.cleaned_data["nombre"])

    def clean_descripcion(self):
        return sanitize_input(self.cleaned_data.get("descripcion", ""))

    def clean(self):
        cleaned = super().clean()
        stock, minimo = cleaned.get("stock"), cleaned.get("stock_minimo")
        if stock is not None and minimo is not None and minimo > 1000:
            self.add_error("stock_minimo", "El stock mínimo no puede superar 1000 unidades.")
        if cleaned.get("activo") and stock == 0:
            raise forms.ValidationError("Un producto activo debe tener al menos 1 unidad en stock.")
        return cleaned


# ---------------------------------------------------------------------------
# 3) Registro de usuarios (extiende UserCreationForm)
# ---------------------------------------------------------------------------
class RegistroForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(label="Nombres", max_length=50, validators=[validar_sin_html])

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ["username", "first_name", "email"]

    def clean_username(self):
        username = sanitize_input(self.cleaned_data["username"], minusculas=True)
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("Ese nombre de usuario ya está registrado.")
        return username

    def clean_email(self):
        email = sanitize_input(self.cleaned_data["email"], minusculas=True)
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Ya existe una cuenta con ese correo.")
        return email
