"""
Middlewares personalizados.
Estructura: __init__(get_response) se ejecuta UNA vez al arrancar el servidor;
__call__(request) se ejecuta en CADA request: código antes de get_response = fase request,
código después = fase response.
"""
import logging
import time

from django.utils import timezone

logger = logging.getLogger("inventario.auditoria")


class RequestLogMiddleware:
    """Registra método, ruta, usuario, IP, status y tiempo de respuesta."""

    def __init__(self, get_response):
        self.get_response = get_response
        logger.info("RequestLogMiddleware inicializado")

    def __call__(self, request):
        inicio = time.perf_counter()                       # --- fase REQUEST
        response = self.get_response(request)              # --- vista (y middlewares internos)
        duracion = (time.perf_counter() - inicio) * 1000   # --- fase RESPONSE
        usuario = request.user.username if getattr(request, "user", None) and request.user.is_authenticated else "anónimo"
        logger.info(
            "%s %s | usuario=%s | ip=%s | status=%s | %.1fms",
            request.method, request.get_full_path(), usuario, self._ip(request), response.status_code, duracion,
        )
        response["X-Tiempo-Respuesta-ms"] = f"{duracion:.1f}"
        return response

    @staticmethod
    def _ip(request):
        xff = request.META.get("HTTP_X_FORWARDED_FOR")
        return xff.split(",")[0].strip() if xff else request.META.get("REMOTE_ADDR")


class SecurityHeadersMiddleware:
    """Añade Content-Security-Policy y Permissions-Policy a todas las respuestas."""

    CSP = (
        "default-src 'self'; "
        "img-src 'self' data:; "
        "style-src 'self' 'unsafe-inline'; "
        "script-src 'self'; "
        "frame-ancestors 'none'; "
        "form-action 'self'; "
        "base-uri 'self'"
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response.setdefault("Content-Security-Policy", self.CSP)
        response.setdefault("Permissions-Policy", "geolocation=(), camera=(), microphone=()")
        return response


class UltimaActividadMiddleware:
    """
    Guarda en la sesión la última actividad y un contador de páginas visitadas
    del usuario autenticado. Muestra el uso correcto de request.session.modified.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            request.session["ultima_actividad"] = timezone.now().isoformat()
            historial = request.session.setdefault("historial", [])
            historial.append(request.path)              # mutación de un objeto interno...
            del historial[:-5]                          # se conservan las últimas 5 rutas
            request.session["paginas_vistas"] = request.session.get("paginas_vistas", 0) + 1
            request.session.modified = True             # ...por eso se marca explícitamente
        return self.get_response(request)
