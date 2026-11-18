"""
Configuración del proyecto - Semana 12: Formularios, Admin, Middleware y Seguridad.
Los valores sensibles se leen de variables de entorno (nunca hardcodear en producción).
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# --- Seguridad básica ------------------------------------------------------
# En producción: definir DJANGO_SECRET_KEY y rotarla periódicamente.
SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "dev-insecure-cambiar-en-produccion-3f9a1c7e5b2d8f4a6c0e9b1d7f3a5c2e",
)
# Nunca DEBUG=True en producción: se controla por variable de entorno.
DEBUG = os.environ.get("DJANGO_DEBUG", "True") == "True"
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_extensions",
    "inventario",
]

# El orden importa: en el request se ejecutan de arriba hacia abajo,
# en el response de abajo hacia arriba (orden inverso / LIFO).
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # Middlewares personalizados (después de Auth para conocer request.user)
    "inventario.middleware.RequestLogMiddleware",
    "inventario.middleware.SecurityHeadersMiddleware",
    "inventario.middleware.UltimaActividadMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "es-pe"
TIME_ZONE = "America/Lima"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Autenticación ---------------------------------------------------------
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "inventario:dashboard"
LOGOUT_REDIRECT_URL = "login"

# --- Sesiones --------------------------------------------------------------
SESSION_ENGINE = "django.contrib.sessions.backends.db"  # sesiones en BD
SESSION_COOKIE_AGE = 60 * 30            # 30 minutos
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_SAVE_EVERY_REQUEST = True       # renueva la expiración en cada request
SESSION_COOKIE_HTTPONLY = True          # JS no puede leer la cookie de sesión
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_NAME = "s12_sessionid"

# --- CSRF ------------------------------------------------------------------
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_FAILURE_VIEW = "inventario.views.csrf_failure"

# --- Cabeceras de seguridad ------------------------------------------------
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"

# En producción (DEBUG=False) se activan las protecciones que requieren HTTPS.
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_SSL_REDIRECT = not DEBUG
SECURE_HSTS_SECONDS = 0 if DEBUG else 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = not DEBUG

# --- Logging (auditoría del middleware) ------------------------------------
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "auditoria": {"format": "[{asctime}] {levelname} {name}: {message}", "style": "{"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "auditoria"},
        "archivo": {
            "class": "logging.FileHandler",
            "filename": LOGS_DIR / "auditoria.log",
            "formatter": "auditoria",
            "encoding": "utf-8",
        },
    },
    "loggers": {
        "inventario.auditoria": {"handlers": ["console", "archivo"], "level": "INFO", "propagate": False},
    },
}
