"""Validadores personalizados y utilidades de sanitización."""
import re

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.utils.html import escape, strip_tags

# Validador regex reutilizable: SKU con formato ABC-1234
validar_codigo_sku = RegexValidator(
    regex=r"^[A-Z]{3}-\d{4}$",
    message="El SKU debe tener el formato ABC-1234 (3 letras mayúsculas, guion, 4 dígitos).",
    code="sku_invalido",
)

# Teléfono peruano: 9 dígitos que empiezan con 9
validar_telefono = RegexValidator(
    regex=r"^9\d{8}$",
    message="Ingrese un celular válido de 9 dígitos que empiece con 9.",
    code="telefono_invalido",
)

PATRON_HTML = re.compile(r"<[^>]+>")
PATRON_SQLI = re.compile(r"(--|;|/\*|\*/|\b(union|select|drop|insert|delete|update)\b\s)", re.IGNORECASE)


def validar_sin_html(valor):
    """Rechaza cualquier etiqueta HTML (prevención de XSS almacenado)."""
    if valor and PATRON_HTML.search(valor):
        raise ValidationError("No se permiten etiquetas HTML.", code="html_no_permitido")


def validar_sin_sql(valor):
    """Rechaza patrones típicos de inyección SQL (defensa adicional; el ORM ya parametriza)."""
    if valor and PATRON_SQLI.search(valor):
        raise ValidationError("El texto contiene patrones no permitidos.", code="sql_sospechoso")


def sanitize_input(valor, *, minusculas=False, escapar=False):
    """
    Sanitización básica de texto antes de persistir:
      - strip(): elimina espacios en los extremos
      - colapsa espacios internos repetidos
      - strip_tags(): quita etiquetas HTML
      - lower(): opcional (emails, usernames)
      - escape(): opcional (convierte < > & ' " a entidades)
    """
    if valor is None:
        return valor
    valor = strip_tags(str(valor)).strip()
    valor = re.sub(r"\s+", " ", valor)
    if minusculas:
        valor = valor.lower()
    if escapar:
        valor = escape(valor)
    return valor
