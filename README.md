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

| Formulario clásico | ModelForm |
|---|---|
| ![](evidencias/01_fase1_codigo_form_clasico.png) | ![](evidencias/02_fase1_codigo_modelform.png) |

| Vista POST | Formulario renderizado |
|---|---|
| ![](evidencias/03_fase1_codigo_vista_post.png) | ![](evidencias/04_fase1_form_clasico_vacio.png) |

## Fase 2 – Validación y sanitización

Tres niveles de validación:
1. **Campo**: validadores regex (`validar_codigo_sku`, `validar_telefono`), `validar_sin_html`, `validar_sin_sql` y los métodos `clean_<campo>()`.
2. **Formulario**: `clean()` cruza campos; `self.add_error()` asocia el error a un campo y `raise ValidationError` lo deja en `__all__`.
3. **Modelo**: `Producto.clean()` verifica que el precio de oferta sea menor que el precio normal.

`sanitize_input()` aplica `strip_tags()`, `strip()`, colapsa los espacios internos y, de forma opcional, `lower()` y `escape()`.

![Código de validadores](evidencias/05_fase2_codigo_validadores_sanitize.png)

| Errores por campo (XSS, SQLi, regex, cross-field) | Error global `__all__` |
|---|---|
| ![](evidencias/06_fase2_errores_por_campo.png) | ![](evidencias/07_fase2_error_global_all.png) |

| Envío correcto | ModelForm: errores de campo, formulario y modelo | Guardado ya sanitizado |
|---|---|---|
| ![](evidencias/08_fase2_contacto_enviado_ok.png) | ![](evidencias/09_fase2_modelform_errores_3_niveles.png) | ![](evidencias/10_fase2_modelform_guardado_sanitizado.png) |

## Fase 3 – Django Admin

- `ProductoAdmin`: `list_display` con los campos calculados `estado_stock` y `valor_inventario_display` (`@admin.display`), `list_filter` con un filtro propio `BajoStockFilter`, `search_fields`, `readonly_fields`, `fieldsets`, `list_select_related` (equivale a `select_related()`) y `date_hierarchy`.
- Acciones masivas: activar, desactivar, reponer stock (`F('stock') + 20`) y exportar a CSV.
- `CategoriaAdmin`: totales calculados con `annotate()` para evitar consultas N+1, más un inline de productos.
- `MensajeContactoAdmin`: todos los campos son de solo lectura y no se permite agregar (`has_add_permission=False`).
- Nunca se exponen campos sensibles: el usuario creador es `readonly` y se asigna en `save_model()`.

![](evidencias/11_fase3_codigo_admin.png)

| Index | list_display + filtros | Filtro personalizado |
|---|---|---|
| ![](evidencias/12_fase3_admin_index.png) | ![](evidencias/13_fase3_admin_list_display_filtros.png) | ![](evidencias/14_fase3_admin_filtro_bajo_stock.png) |

| search_fields | Acción masiva | Acción ejecutada |
|---|---|---|
| ![](evidencias/15_fase3_admin_search_fields.png) | ![](evidencias/16_fase3_admin_accion_masiva_seleccion.png) | ![](evidencias/17_fase3_admin_accion_ejecutada.png) |

| readonly_fields | Categorías (campos calculados) | Mensajes | Rol Editores |
|---|---|---|---|
| ![](evidencias/18_fase3_admin_readonly_fields.png) | ![](evidencias/19_fase3_admin_categoria_campos_calculados.png) | ![](evidencias/20_fase3_admin_mensajes_contacto.png) | ![](evidencias/21_fase3_admin_rol_editores_permisos.png) |

## Fase 4 – Middleware, sesiones y autorización

- `RequestLogMiddleware`: registra método, ruta, usuario, IP, status y tiempo en `logs/auditoria.log`, y añade la cabecera `X-Tiempo-Respuesta-ms`.
- `SecurityHeadersMiddleware`: añade `Content-Security-Policy` y `Permissions-Policy`.
- `UltimaActividadMiddleware`: guarda en la sesión la última actividad y el historial de rutas, y marca `request.session.modified = True` porque modifica una lista mutable.
- Sesiones: `SESSION_ENGINE=db`, `SESSION_COOKIE_AGE=1800`, `HTTPONLY`, `SameSite=Lax`, expiran al cerrar el navegador.
- CSRF: `CSRF_COOKIE_SECURE` y `SESSION_COOKIE_SECURE` se activan con `DEBUG=False`; hay una vista propia `CSRF_FAILURE_VIEW`.
- `@login_required`, `@permission_required`, `LoginRequiredMixin`, `PermissionRequiredMixin` y `user.has_perm()`.

| Middleware | Orden en `MIDDLEWARE` |
|---|---|
| ![](evidencias/22_fase4_codigo_middleware.png) | ![](evidencias/23_fase4_codigo_settings_middleware.png) |

| Sesiones / CSRF / seguridad | login_required y PermissionRequiredMixin |
|---|---|
| ![](evidencias/24_fase4_codigo_settings_sesiones_csrf.png) | ![](evidencias/25_fase4_codigo_login_required_permission_mixin.png) |

| Redirección a LOGIN_URL | Sesión y permisos (lector) | 403 por permiso |
|---|---|---|
| ![](evidencias/26_fase4_login_required_redireccion.png) | ![](evidencias/27_fase4_dashboard_lector_sesion_permisos.png) | ![](evidencias/28_fase4_lector_403_permission_required.png) |

| No staff → sin acceso al admin | POST sin token CSRF → 403 |
|---|---|
| ![](evidencias/29_fase4_lector_sin_acceso_admin.png) | ![](evidencias/30_fase4_csrf_token_ausente_403.png) |

## Fase 5 – Integración y auditoría

Flujo completo: **registro → login → acceso restringido → admin → logout**.

| Registro con errores | Registro OK con login automático | Usuario nuevo sin permiso |
|---|---|---|
| ![](evidencias/31_fase5_registro_errores.png) | ![](evidencias/32_fase5_registro_ok_login_automatico.png) | ![](evidencias/33_fase5_usuario_nuevo_sin_permiso_403.png) |

| Logout | Login de editor | Reportes (con permiso) |
|---|---|---|
| ![](evidencias/34_fase5_logout.png) | ![](evidencias/35_fase5_login_editor_dashboard.png) | ![](evidencias/36_fase5_editor_reportes.png) |

| Cookies y cabeceras (X-Frame-Options, CSP…) | Logs del middleware |
|---|---|
| ![](evidencias/37_fase5_devtools_cookies_headers.png) | ![](evidencias/38_fase5_logs_middleware.png) |

| Migraciones | Pruebas (17 OK) |
|---|---|
| ![](evidencias/39_fase5_terminal_migraciones.png) | ![](evidencias/40_fase5_terminal_tests.png) |

| `check --deploy` en desarrollo (5 avisos esperados) | `check --deploy` en producción (0 issues) |
|---|---|
| ![](evidencias/41_fase5_check_deploy_desarrollo.png) | ![](evidencias/42_fase5_check_deploy_produccion.png) |

### Producción

```powershell
$env:DJANGO_DEBUG="False"
$env:DJANGO_SECRET_KEY = python -c "from django.core.management.utils import get_random_secret_key as g; print(g())"
$env:DJANGO_ALLOWED_HOSTS="midominio.com"
python manage.py check --deploy
```

`DEBUG`, `SECRET_KEY` y `ALLOWED_HOSTS` se leen de variables de entorno. Para rotar la `SECRET_KEY` basta con generar una nueva y reiniciar el servidor; las sesiones anteriores quedan invalidadas.

**Ciclo de un request:** Request → Middleware (de arriba a abajo) → URL Resolver → View → Form → Model → DB → Template → Response → Middleware (en orden inverso).
