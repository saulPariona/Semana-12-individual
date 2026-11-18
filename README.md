# Semana 12 – Formularios, Admin, Middleware y Seguridad en Django 5

Sistema backend de **inventario** que cubre el ciclo completo de gestión de datos y seguridad en Django 5.2:
formularios (`Form` y `ModelForm`), validación en 3 niveles, sanitización, Django Admin personalizado,
middleware propio, sesiones seguras, autenticación, autorización por roles/permisos y protección CSRF.

## Instalación y ejecución

```powershell
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py cargar_demo        # roles, usuarios y productos de prueba
python manage.py runserver
```

| Usuario | Contraseña | Rol |
|---|---|---|
| `admin` | `Admin12345!` | Superusuario |
| `editor` | `Editor12345!` | Grupo **Editores** (staff, add/change producto, ver_reportes) |
| `lector` | `Lector12345!` | Grupo **Lectores** (solo lectura, sin admin) |

Pruebas: `python manage.py test inventario` (17 pruebas).  
Capturas: `pip install playwright pygments` y `python scripts/capturas.py .` con el servidor levantado.

## Estructura

```
config/settings.py        Sesiones, CSRF, cabeceras de seguridad, logging, valores por variable de entorno
inventario/
  forms.py                ContactoForm (clásico), ProductoForm (ModelForm), RegistroForm
  validators.py           Validadores regex, anti-HTML, anti-SQLi y sanitize_input()
  models.py               Categoria, Producto (clean() de modelo, permiso ver_reportes), MensajeContacto
  admin.py                list_display, list_filter, search_fields, readonly_fields, actions, @admin.display
  middleware.py           RequestLogMiddleware, SecurityHeadersMiddleware (CSP), UltimaActividadMiddleware
  views.py                @login_required, @permission_required, LoginRequiredMixin, PermissionRequiredMixin
  management/commands/cargar_demo.py
  tests.py                17 pruebas: validación, sanitización, auth, permisos, CSRF, middleware
templates/                base, formularios, dashboard, login/registro, 403, 403_csrf
evidencias/               Capturas de pantalla de cada fase
```

---

## Fase 1 – Formularios y plantillas

- `ContactoForm(forms.Form)`: formulario clásico, no ligado a un modelo; su método `guardar()` solo usa `cleaned_data`.
- `ProductoForm(forms.ModelForm)`: los campos y validadores se generan a partir del modelo `Producto`.
- Las vistas **nunca** guardan desde `request.POST`: siempre `Form(request.POST)` → `is_valid()` → `save()`, y después redirigen (patrón PRG).
- Las plantillas usan `{% csrf_token %}`, `{{ form.as_p }}` y `{{ form.errors }}`.



## Fase 2 – Validación y sanitización

Tres niveles de validación:
1. **Campo**: validadores regex (`validar_codigo_sku`, `validar_telefono`), `validar_sin_html`, `validar_sin_sql` y los métodos `clean_<campo>()`.
2. **Formulario**: `clean()` cruza campos; `self.add_error()` asocia el error a un campo y `raise ValidationError` lo deja en `__all__`.
3. **Modelo**: `Producto.clean()` verifica que el precio de oferta sea menor que el precio normal.

`sanitize_input()` aplica `strip_tags()`, `strip()`, colapsa los espacios internos y, de forma opcional, `lower()` y `escape()`.


## Fase 3 – Django Admin

- `ProductoAdmin`: `list_display` con los campos calculados `estado_stock` y `valor_inventario_display` (`@admin.display`), `list_filter` con un filtro propio `BajoStockFilter`, `search_fields`, `readonly_fields`, `fieldsets`, `list_select_related` (equivale a `select_related()`) y `date_hierarchy`.
- Acciones masivas: activar, desactivar, reponer stock (`F('stock') + 20`) y exportar a CSV.
- `CategoriaAdmin`: totales calculados con `annotate()` para evitar consultas N+1, más un inline de productos.
- `MensajeContactoAdmin`: todos los campos son de solo lectura y no se permite agregar (`has_add_permission=False`).
- Nunca se exponen campos sensibles: el usuario creador es `readonly` y se asigna en `save_model()`.



## Fase 4 – Middleware, sesiones y autorización

- `RequestLogMiddleware`: registra método, ruta, usuario, IP, status y tiempo en `logs/auditoria.log`, y añade la cabecera `X-Tiempo-Respuesta-ms`.
- `SecurityHeadersMiddleware`: añade `Content-Security-Policy` y `Permissions-Policy`.
- `UltimaActividadMiddleware`: guarda en la sesión la última actividad y el historial de rutas, y marca `request.session.modified = True` porque modifica una lista mutable.
- Sesiones: `SESSION_ENGINE=db`, `SESSION_COOKIE_AGE=1800`, `HTTPONLY`, `SameSite=Lax`, expiran al cerrar el navegador.
- CSRF: `CSRF_COOKIE_SECURE` y `SESSION_COOKIE_SECURE` se activan con `DEBUG=False`; hay una vista propia `CSRF_FAILURE_VIEW`.
- `@login_required`, `@permission_required`, `LoginRequiredMixin`, `PermissionRequiredMixin` y `user.has_perm()`.


## Fase 5 – Integración y auditoría

Flujo completo: **registro → login → acceso restringido → admin → logout**.



### Producción

```powershell
$env:DJANGO_DEBUG="False"
$env:DJANGO_SECRET_KEY = python -c "from django.core.management.utils import get_random_secret_key as g; print(g())"
$env:DJANGO_ALLOWED_HOSTS="midominio.com"
python manage.py check --deploy
```

`DEBUG`, `SECRET_KEY` y `ALLOWED_HOSTS` se leen de variables de entorno. Para rotar la `SECRET_KEY` basta con generar una nueva y reiniciar el servidor; las sesiones anteriores quedan invalidadas.

**Ciclo de un request:** Request → Middleware (de arriba a abajo) → URL Resolver → View → Form → Model → DB → Template → Response → Middleware (en orden inverso).
