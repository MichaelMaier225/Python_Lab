"""
Django settings for the Sacratissimum project.

Local development and free, disposable Render preview configuration.
"""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

# Render is HTTPS-only. A local run stays in development mode unless opted out.
IS_RENDER = os.environ.get("RENDER", "").lower() == "true"
PREVIEW_MODE = os.environ.get("SACRATISSIMUM_PREVIEW", "").lower() == "true"
DEBUG = os.environ.get(
    "DJANGO_DEBUG", "false" if IS_RENDER or PREVIEW_MODE else "true"
).lower() == "true"
if IS_RENDER and DEBUG:
    raise ImproperlyConfigured("DJANGO_DEBUG must be false on Render.")

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
if not SECRET_KEY:
    if not DEBUG:
        raise ImproperlyConfigured("Set DJANGO_SECRET_KEY when DJANGO_DEBUG=false.")
    SECRET_KEY = "local-development-only-not-for-production-sacratissimum"

ALLOWED_HOSTS = [host.strip() for host in os.environ.get(
    "DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1" if DEBUG else ""
).split(",") if host.strip()]
# Render supplies the exact assigned hostname, including any generated suffix.
# Do not allow every onrender.com site or use a wildcard.
RENDER_HOSTNAME = os.environ.get("RENDER_EXTERNAL_HOSTNAME", "").strip()
if IS_RENDER and RENDER_HOSTNAME and RENDER_HOSTNAME not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(RENDER_HOSTNAME)

CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in os.environ.get(
    "DJANGO_CSRF_TRUSTED_ORIGINS", ""
).split(",") if origin.strip()]
if IS_RENDER and RENDER_HOSTNAME:
    render_origin = f"https://{RENDER_HOSTNAME}"
    if render_origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(render_origin)
    # Render terminates TLS and sets this header before forwarding to Gunicorn.
    # Trust it only in the Render environment, not arbitrary local requests.
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_SSL_REDIRECT = True

# HSTS/preloading is deliberately not configured for this disposable preview.
# Django check --deploy reports security.W004; do not silence that advisory.

# Applications

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "store.apps.StoreConfig",
]


# Middleware

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


# URLs and templates

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "store.context_processors.asset_version",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


# Database

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.environ.get(
            "SACRATISSIMUM_DB_PATH",
            "/tmp/sacratissimum-preview.sqlite3" if PREVIEW_MODE else BASE_DIR / "local.sqlite3",
        ),
    }
}


# Password validation

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "UserAttributeSimilarityValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "MinimumLengthValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "CommonPasswordValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "NumericPasswordValidator"
        ),
    },
]


# Language and time zone

LANGUAGE_CODE = "en-us"

TIME_ZONE = "America/Chicago"

USE_I18N = True

USE_TZ = True


# Static files: CSS, JavaScript, and site images

STATIC_URL = "/static/"

STATIC_ROOT = BASE_DIR / "staticfiles"

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage" if DEBUG
        else "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}
# In production, WhiteNoise serves collectstatic output, not source directories.
WHITENOISE_USE_FINDERS = DEBUG
WHITENOISE_AUTOREFRESH = DEBUG


# Uploaded files: product photos

MEDIA_URL = "/media/"

MEDIA_ROOT = BASE_DIR / "media"


# Email: print emails in the terminal during development

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
