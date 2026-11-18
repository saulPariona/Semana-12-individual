"""Carga datos de demostración: grupos/roles con permisos, usuarios, categorías y productos.
Uso: python manage.py cargar_demo
"""
from decimal import Decimal

from django.contrib.auth.models import Group, Permission, User
from django.core.management.base import BaseCommand

from inventario.models import Categoria, Producto

ROLES = {
    "Editores": ["view_producto", "add_producto", "change_producto", "view_categoria", "ver_reportes"],
    "Lectores": ["view_producto", "view_categoria"],
}

USUARIOS = [
    # username, password, grupo, is_staff, is_superuser
    ("admin", "Admin12345!", None, True, True),
    ("editor", "Editor12345!", "Editores", True, False),
    ("lector", "Lector12345!", "Lectores", False, False),
]

PRODUCTOS = [
    ("LAP-1001", "Laptop Lenovo ThinkPad", "Computo", "3500.00", None, 12),
    ("MOU-2001", "Mouse inalámbrico", "Periféricos", "45.90", "39.90", 3),
    ("TEC-2002", "Teclado mecánico", "Periféricos", "199.00", None, 25),
    ("MON-3001", "Monitor 27 pulgadas", "Computo", "1200.00", "1099.00", 4),
    ("CAB-4001", "Cable HDMI 2m", "Accesorios", "25.00", None, 0),
    ("AUD-4002", "Audífonos Bluetooth", "Accesorios", "150.00", None, 40),
]


class Command(BaseCommand):
    help = "Crea roles, usuarios y datos de demostración"

    def handle(self, *args, **opts):
        for nombre, codenames in ROLES.items():
            grupo, _ = Group.objects.get_or_create(name=nombre)
            grupo.permissions.set(Permission.objects.filter(content_type__app_label="inventario", codename__in=codenames))
            self.stdout.write(f"Grupo {nombre}: {', '.join(codenames)}")

        for username, pwd, grupo, staff, su in USUARIOS:
            user, creado = User.objects.get_or_create(username=username, defaults={"email": f"{username}@demo.pe"})
            user.is_staff, user.is_superuser = staff, su
            user.set_password(pwd)
            user.save()
            if grupo:
                user.groups.set([Group.objects.get(name=grupo)])
            self.stdout.write(f"Usuario {username} / {pwd}")

        admin = User.objects.get(username="admin")
        for sku, nombre, cat, precio, oferta, stock in PRODUCTOS:
            categoria, _ = Categoria.objects.get_or_create(nombre=cat)
            Producto.objects.update_or_create(sku=sku, defaults={
                "nombre": nombre, "categoria": categoria, "precio": Decimal(precio),
                "precio_oferta": Decimal(oferta) if oferta else None, "stock": stock,
                "activo": stock > 0, "creado_por": admin,
            })
        self.stdout.write(self.style.SUCCESS("Datos de demostración cargados."))
