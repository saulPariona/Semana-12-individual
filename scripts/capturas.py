"""Recorre el flujo completo y genera capturas en evidencias/."""
import html
import os
import re
import subprocess
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import PythonLexer

ROOT = Path(sys.argv[1])
OUT = ROOT / "evidencias"
OUT.mkdir(exist_ok=True)
PY = str(ROOT / "venv" / "Scripts" / "python.exe")
URL = "http://127.0.0.1:8000"
n = 0


def shot(page, nombre, full=True):
    global n
    n += 1
    path = OUT / f"{n:02d}_{nombre}.png"
    page.screenshot(path=str(path), full_page=full)
    print("captura", path.name)


def terminal_html(titulo, comando, salida):
    return f"""<html><body style="margin:0;background:#1e1e1e;font-family:Consolas,monospace">
<div style="background:#323233;color:#ccc;padding:8px 14px;font:13px Segoe UI">TERMINAL — {html.escape(titulo)}</div>
<pre style="color:#d4d4d4;padding:14px;margin:0;font-size:13px;white-space:pre-wrap">
<span style="color:#4ec9b0">(venv) PS C:\\DAW\\SEMANA12 INDIVIDUAL&gt;</span> <span style="color:#dcdcaa">{html.escape(comando)}</span>
{html.escape(salida)}</pre></body></html>"""


def codigo_html(ruta, desde=None, hasta=None):
    lineas = (ROOT / ruta).read_text(encoding="utf-8").splitlines()
    ini = desde or 1
    fragmento = "\n".join(lineas[ini - 1:hasta])
    fmt = HtmlFormatter(style="monokai", linenos="table", linenostart=ini, noclasses=True)
    return f"""<html><body style="margin:0;background:#272822">
<div style="background:#323233;color:#ccc;padding:8px 14px;font:13px Segoe UI">VS Code — {html.escape(ruta)}</div>
<div style="font-size:13px;padding:8px">{highlight(fragmento, PythonLexer(), fmt)}</div></body></html>"""


def run(cmd, env=None):
    r = subprocess.run([PY, "manage.py", *cmd], cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", env={**os.environ, **(env or {})})
    return (r.stdout + r.stderr).strip()


def render(page, contenido, nombre):
    page.set_content(contenido)
    shot(page, nombre)


def submit(page, sel):
    with page.expect_navigation():
        page.click(sel)


def login(page, user, pwd):
    page.goto(f"{URL}/login/")
    page.fill("#id_username", user)
    page.fill("#id_password", pwd)
    submit(page, "main button[type=submit]")


def logout(page):
    submit(page, "nav button:has-text('Cerrar sesión')")


with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge")
    ctx = browser.new_context(viewport={"width": 1280, "height": 800}, locale="es-PE")
    page = ctx.new_page()
    code = browser.new_page(viewport={"width": 1100, "height": 700})

    # ======================= FASE 1: Formularios & Plantillas ================
    render(code, codigo_html("inventario/forms.py", 1, 70), "fase1_codigo_form_clasico")
    render(code, codigo_html("inventario/forms.py", 71, 108), "fase1_codigo_modelform")
    render(code, codigo_html("inventario/views.py", 18, 30), "fase1_codigo_vista_post")
    page.goto(f"{URL}/contacto/")
    shot(page, "fase1_form_clasico_vacio")

    # ======================= FASE 2: Validación & Sanitización ===============
    render(code, codigo_html("inventario/validators.py"), "fase2_codigo_validadores_sanitize")
    page.fill("#id_nombre", "<script>alert(1)</script>")
    page.fill("#id_email", "ana@mail.com")
    page.fill("#id_confirmar_email", "otra@mail.com")
    page.fill("#id_telefono", "12345")
    page.fill("#id_asunto", "x'; DROP TABLE users; --")
    page.fill("#id_mensaje", "Gana dinero gratis en el casino")
    submit(page, "main button[type=submit]")
    shot(page, "fase2_errores_por_campo")
    page.fill("#id_nombre", "ana perez")
    page.fill("#id_email", "Ana@Mail.com")
    page.fill("#id_confirmar_email", "ana@mail.com")
    page.fill("#id_telefono", "987654321")
    page.fill("#id_asunto", "Consulta de stock disponible")
    page.fill("#id_mensaje", "consulta de stock disponible")
    page.check("#id_acepta_terminos")
    submit(page, "main button[type=submit]")
    shot(page, "fase2_error_global_all")
    page.fill("#id_mensaje", "   Quisiera saber si tienen    <b>laptops</b> en stock.  ")
    page.check("#id_acepta_terminos")
    submit(page, "main button[type=submit]")
    shot(page, "fase2_contacto_enviado_ok")

    login(page, "editor", "Editor12345!")
    page.goto(f"{URL}/productos/nuevo/")
    page.fill("#id_sku", "abc12")
    page.fill("#id_nombre", "Impresora <i>HP</i>")
    page.select_option("#id_categoria", label="Computo")
    page.fill("#id_precio", "500")
    page.fill("#id_precio_oferta", "600")
    page.fill("#id_stock", "0")
    page.fill("#id_stock_minimo", "2000")
    submit(page, "main button[type=submit]")
    shot(page, "fase2_modelform_errores_3_niveles")
    page.fill("#id_sku", "imp-5001")
    page.fill("#id_nombre", "  Impresora   HP LaserJet ")
    page.fill("#id_precio_oferta", "450")
    page.fill("#id_stock", "8")
    page.fill("#id_stock_minimo", "3")
    submit(page, "main button[type=submit]")
    shot(page, "fase2_modelform_guardado_sanitizado")
    logout(page)

    # ======================= FASE 3: Django Admin ============================
    render(code, codigo_html("inventario/admin.py", 1, 75), "fase3_codigo_admin")
    page.goto(f"{URL}/admin/")
    page.fill("#id_username", "admin")
    page.fill("#id_password", "Admin12345!")
    submit(page, "input[type=submit]")
    shot(page, "fase3_admin_index")
    page.goto(f"{URL}/admin/inventario/producto/")
    shot(page, "fase3_admin_list_display_filtros")
    page.goto(f"{URL}/admin/inventario/producto/?nivel=bajo")
    shot(page, "fase3_admin_filtro_bajo_stock")
    page.goto(f"{URL}/admin/inventario/producto/?q=mouse")
    shot(page, "fase3_admin_search_fields")
    page.goto(f"{URL}/admin/inventario/producto/?nivel=bajo")
    page.check("#action-toggle")
    page.select_option("select[name=action]", "reponer_stock")
    shot(page, "fase3_admin_accion_masiva_seleccion")
    submit(page, "button[name=index]")
    page.wait_for_load_state()
    shot(page, "fase3_admin_accion_ejecutada")
    page.goto(f"{URL}/admin/inventario/producto/")
    page.click("text=LAP-1001")
    for s in page.locator("fieldset details summary, fieldset.collapse summary").all():
        s.click()
    shot(page, "fase3_admin_readonly_fields")
    page.goto(f"{URL}/admin/inventario/categoria/")
    shot(page, "fase3_admin_categoria_campos_calculados")
    page.goto(f"{URL}/admin/inventario/mensajecontacto/")
    shot(page, "fase3_admin_mensajes_contacto")
    page.goto(f"{URL}/admin/auth/group/")
    page.click("text=Editores")
    shot(page, "fase3_admin_rol_editores_permisos")
    submit(page, "#logout-form button")
    page.wait_for_load_state()

    # ======================= FASE 4: Middleware & Sesiones ===================
    render(code, codigo_html("inventario/middleware.py"), "fase4_codigo_middleware")
    s = (ROOT / "config/settings.py").read_text(encoding="utf-8").splitlines()
    a = next(i for i, l in enumerate(s) if l.startswith("MIDDLEWARE"))
    render(code, codigo_html("config/settings.py", a + 1, a + 15), "fase4_codigo_settings_middleware")
    b = next(i for i, l in enumerate(s) if "Autenticación" in l)
    render(code, codigo_html("config/settings.py", b + 1, b + 40), "fase4_codigo_settings_sesiones_csrf")
    render(code, codigo_html("inventario/views.py", 46, 120), "fase4_codigo_login_required_permission_mixin")
    page.goto(f"{URL}/dashboard/")
    shot(page, "fase4_login_required_redireccion")
    page.fill("#id_username", "lector")
    page.fill("#id_password", "Lector12345!")
    submit(page, "main button[type=submit]")
    page.goto(f"{URL}/productos/")
    page.goto(f"{URL}/dashboard/")
    shot(page, "fase4_dashboard_lector_sesion_permisos")
    page.goto(f"{URL}/reportes/")
    shot(page, "fase4_lector_403_permission_required")
    page.goto(f"{URL}/admin/")
    shot(page, "fase4_lector_sin_acceso_admin")
    page.goto(f"{URL}/dashboard/")
    logout(page)
    page.goto(f"{URL}/contacto/")
    page.evaluate("document.querySelector('input[name=csrfmiddlewaretoken]').remove()")
    page.fill("#id_nombre", "Atacante")
    submit(page, "main button[type=submit]")
    shot(page, "fase4_csrf_token_ausente_403")

    # ======================= FASE 5: Integración & Auditoría =================
    page.goto(f"{URL}/registro/")
    page.fill("#id_username", "Saul")
    page.fill("#id_first_name", "Saul")
    page.fill("#id_email", "saul@demo.pe")
    page.fill("#id_password1", "123")
    page.fill("#id_password2", "456")
    submit(page, "main button[type=submit]")
    shot(page, "fase5_registro_errores")
    page.fill("#id_password1", "ClaveSegura#2026")
    page.fill("#id_password2", "ClaveSegura#2026")
    submit(page, "main button[type=submit]")
    shot(page, "fase5_registro_ok_login_automatico")
    page.goto(f"{URL}/productos/nuevo/")
    shot(page, "fase5_usuario_nuevo_sin_permiso_403")
    logout(page)
    shot(page, "fase5_logout")
    login(page, "editor", "Editor12345!")
    resp = page.goto(f"{URL}/dashboard/")
    shot(page, "fase5_login_editor_dashboard")
    page.goto(f"{URL}/reportes/")
    shot(page, "fase5_editor_reportes")

    # Inspección tipo DevTools: cookies y cabeceras
    cookies = ctx.cookies()
    filas = "".join(
        f"<tr><td>{c['name']}</td><td>{html.escape(c['value'][:24])}…</td><td>{c['domain']}</td>"
        f"<td>{'✔' if c['httpOnly'] else ''}</td><td>{'✔' if c['secure'] else ''}</td><td>{c['sameSite']}</td>"
        f"<td>{'Sesión' if c['expires'] == -1 else 'Persistente'}</td></tr>" for c in cookies)
    hdrs = "".join(f"<tr><td><b>{k}</b></td><td>{html.escape(v)}</td></tr>" for k, v in sorted(resp.headers.items()))
    devtools = f"""<html><body style="font:13px Segoe UI;margin:0">
<div style="background:#f3f3f3;border-bottom:1px solid #ccc;padding:8px">DevTools — Application ▸ Cookies ▸ {URL} &nbsp;|&nbsp; Network ▸ GET /dashboard/ (200)</div>
<div style="padding:12px"><h3>Cookies</h3><table border=1 cellpadding=6 style="border-collapse:collapse">
<tr style="background:#eee"><th>Name</th><th>Value</th><th>Domain</th><th>HttpOnly</th><th>Secure</th><th>SameSite</th><th>Expira</th></tr>{filas}</table>
<p style="color:#666">Secure=False en desarrollo (HTTP). Con DJANGO_DEBUG=False → SESSION_COOKIE_SECURE y CSRF_COOKIE_SECURE = True.</p>
<h3>Response Headers</h3><table border=1 cellpadding=6 style="border-collapse:collapse">{hdrs}</table></div></body></html>"""
    render(code, devtools, "fase5_devtools_cookies_headers")
    logout(page)

    # Evidencias de terminal
    log = (ROOT / "logs" / "auditoria.log").read_text(encoding="utf-8").splitlines()
    render(code, terminal_html("logs de middleware", "Get-Content logs\\auditoria.log -Tail 40", "\n".join(log[-40:])), "fase5_logs_middleware")
    render(code, terminal_html("migraciones", "python manage.py showmigrations inventario", run(["showmigrations", "inventario"])), "fase5_terminal_migraciones")
    salida = run(["test", "inventario", "-v", "2"])
    salida = "\n".join(l for l in salida.splitlines() if "auditoria" not in l)
    render(code, terminal_html("tests", "python manage.py test inventario -v 2", salida), "fase5_terminal_tests")
    render(code, terminal_html("check --deploy (desarrollo)", "python manage.py check --deploy", run(["check", "--deploy"])), "fase5_check_deploy_desarrollo")
    from django.core.management.utils import get_random_secret_key
    prod = {"DJANGO_DEBUG": "False", "DJANGO_SECRET_KEY": get_random_secret_key()}
    render(code, terminal_html("check --deploy (producción)",
                               '$env:DJANGO_DEBUG="False"; $env:DJANGO_SECRET_KEY="<nueva clave rotada>"; python manage.py check --deploy',
                               run(["check", "--deploy"], prod)), "fase5_check_deploy_produccion")
    browser.close()
