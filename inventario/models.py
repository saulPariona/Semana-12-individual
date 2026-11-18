from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

from .validators import validar_codigo_sku, validar_sin_html


class Categoria(models.Model):
    nombre = models.CharField(max_length=80, unique=True, validators=[validar_sin_html])
    descripcion = models.TextField(blank=True)
    activa = models.BooleanField(default=True)

    class Meta:
        ordering = ["nombre"]
        verbose_name = "categoría"
        verbose_name_plural = "categorías"

    def __str__(self):
        return self.nombre


class Producto(models.Model):
    sku = models.CharField("SKU", max_length=12, unique=True, validators=[validar_codigo_sku],
                           help_text="Formato: ABC-1234")
    nombre = models.CharField(max_length=120, validators=[validar_sin_html])
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, related_name="productos")
    descripcion = models.TextField(blank=True)
    precio = models.DecimalField(max_digits=10, decimal_places=2,
                                 validators=[MinValueValidator(Decimal("0.01"))])
    precio_oferta = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    stock = models.PositiveIntegerField(default=0)
    stock_minimo = models.PositiveIntegerField(default=5)
    activo = models.BooleanField(default=True)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                   null=True, blank=True, related_name="productos_creados")
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-creado"]
        permissions = [
            ("ver_reportes", "Puede ver reportes de inventario"),
        ]

    def __str__(self):
        return f"{self.sku} - {self.nombre}"

    # Nivel 3 de validación: modelo
    def clean(self):
        if self.precio_oferta is not None and self.precio is not None and self.precio_oferta >= self.precio:
            raise ValidationError({"precio_oferta": "El precio de oferta debe ser menor al precio normal."})

    @property
    def valor_inventario(self):
        return (self.precio_oferta or self.precio) * self.stock

    @property
    def bajo_stock(self):
        return self.stock <= self.stock_minimo


class MensajeContacto(models.Model):
    nombre = models.CharField(max_length=100)
    email = models.EmailField()
    asunto = models.CharField(max_length=150)
    mensaje = models.TextField()
    ip = models.GenericIPAddressField(null=True, blank=True)
    atendido = models.BooleanField(default=False)
    recibido = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-recibido"]
        verbose_name = "mensaje de contacto"
        verbose_name_plural = "mensajes de contacto"

    def __str__(self):
        return f"{self.asunto} ({self.email})"
