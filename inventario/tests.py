from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import Client, TestCase
from django.urls import reverse

from .forms import ContactoForm, ProductoForm
from .models import Categoria, MensajeContacto
from .validators import sanitize_input


class SanitizacionTests(TestCase):
    def test_sanitize_input(self):
        self.assertEqual(sanitize_input("  <b>Hola</b>   mundo  "), "Hola mundo")
        self.assertEqual(sanitize_input(" USER@Mail.COM ", minusculas=True), "user@mail.com")
        self.assertEqual(sanitize_input("a & b", escapar=True), "a &amp; b")


class ContactoFormTests(TestCase):
    base = {"nombre": "ana perez", "email": "Ana@Mail.com", "confirmar_email": "ana@mail.com",
            "asunto": "Consulta", "mensaje": "Quisiera información del producto", "acepta_terminos": "on"}

    def test_valido_y_normaliza(self):
        f = ContactoForm(self.base)
        self.assertTrue(f.is_valid(), f.errors)
        self.assertEqual(f.cleaned_data["nombre"], "Ana Perez")
        self.assertEqual(f.cleaned_data["email"], "ana@mail.com")

    def test_emails_no_coinciden(self):
        f = ContactoForm({**self.base, "confirmar_email": "otro@mail.com"})
        self.assertFalse(f.is_valid())
        self.assertIn("confirmar_email", f.errors)

    def test_error_global_all(self):
        f = ContactoForm({**self.base, "asunto": "Hola que tal amigo", "mensaje": "hola que tal amigo"})
        self.assertFalse(f.is_valid())
        self.assertIn("__all__", f.errors)

    def test_xss_rechazado(self):
        f = ContactoForm({**self.base, "nombre": "<script>alert(1)</script>"})
        self.assertFalse(f.is_valid())
        self.assertIn("nombre", f.errors)

    def test_sqli_rechazado(self):
        f = ContactoForm({**self.base, "asunto": "x'; DROP TABLE users; --"})
        self.assertFalse(f.is_valid())
        self.assertIn("asunto", f.errors)


class ProductoFormTests(TestCase):
    def setUp(self):
        self.cat = Categoria.objects.create(nombre="Computo")

    def datos(self, **kw):
        d = {"sku": "lap-1234", "nombre": "Laptop", "categoria": self.cat.pk, "precio": "100",
             "stock": "5", "stock_minimo": "2", "activo": "on"}
        d.update(kw)
        return d

    def test_sku_normalizado(self):
        f = ProductoForm(self.datos())
        self.assertTrue(f.is_valid(), f.errors)
        self.assertEqual(f.cleaned_data["sku"], "LAP-1234")

    def test_sku_regex(self):
        self.assertIn("sku", ProductoForm(self.datos(sku="12")).errors)

    def test_validacion_modelo_precio_oferta(self):
        self.assertIn("precio_oferta", ProductoForm(self.datos(precio_oferta="150")).errors)

    def test_activo_sin_stock(self):
        self.assertIn("__all__", ProductoForm(self.datos(stock="0")).errors)


class AuthYPermisosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("cargar_demo", stdout=StringIO())

    def test_login_required_redirige(self):
        r = self.client.get(reverse("inventario:dashboard"))
        self.assertRedirects(r, f"{reverse('login')}?next={reverse('inventario:dashboard')}")

    def test_lector_sin_permiso_403(self):
        self.client.login(username="lector", password="Lector12345!")
        self.assertEqual(self.client.get(reverse("inventario:producto_crear")).status_code, 403)
        self.assertEqual(self.client.get(reverse("inventario:reporte")).status_code, 403)

    def test_editor_con_permiso(self):
        self.client.login(username="editor", password="Editor12345!")
        self.assertEqual(self.client.get(reverse("inventario:producto_crear")).status_code, 200)
        self.assertEqual(self.client.get(reverse("inventario:reporte")).status_code, 200)

    def test_registro_login_logout(self):
        r = self.client.post(reverse("registro"), {"username": "Nuevo", "first_name": "Nuevo", "email": "n@x.pe",
                                                     "password1": "ClaveSegura#2026", "password2": "ClaveSegura#2026"})
        self.assertRedirects(r, reverse("inventario:dashboard"))
        self.assertTrue(User.objects.filter(username="nuevo").exists())
        self.client.post(reverse("logout"))
        self.assertEqual(self.client.get(reverse("inventario:dashboard")).status_code, 302)

    def test_middleware_headers_y_sesion(self):
        self.client.login(username="editor", password="Editor12345!")
        r = self.client.get(reverse("inventario:dashboard"))
        self.assertIn("Content-Security-Policy", r.headers)
        self.assertEqual(r.headers["X-Frame-Options"], "DENY")
        self.assertIn("X-Tiempo-Respuesta-ms", r.headers)
        self.assertEqual(self.client.session["paginas_vistas"], 1)

    def test_csrf_obligatorio(self):
        c = Client(enforce_csrf_checks=True)
        r = c.post(reverse("inventario:contacto"), ContactoFormTests.base)
        self.assertEqual(r.status_code, 403)
        self.assertEqual(MensajeContacto.objects.count(), 0)

    def test_admin_solo_staff(self):
        self.client.login(username="lector", password="Lector12345!")
        self.assertEqual(self.client.get("/admin/").status_code, 302)
        self.client.login(username="admin", password="Admin12345!")
        self.assertEqual(self.client.get("/admin/inventario/producto/").status_code, 200)
