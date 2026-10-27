"""
Django settings for the Sacratissimum project.

Local development and free, disposable Render preview configuration.
"""

import os
from datetime import timedelta

import dj_database_url
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
    "commerce.apps.CommerceConfig",
    "axes",
    "django_otp",
    "django_otp.plugins.otp_totp",
]


# Middleware

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django_otp.middleware.OTPMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "axes.middleware.AxesMiddleware",
    "commerce.middleware.LoginThrottleMiddleware",
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
                "commerce.context_processors.shop",
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

# Commerce is staged: the disposable demo must not accept customer data or money.
DATABASE_URL = os.environ.get("DATABASE_URL", "")
if DATABASE_URL:
    if PREVIEW_MODE:
        raise ImproperlyConfigured("Disposable preview must use SQLite. Disable SACRATISSIMUM_PREVIEW before connecting PostgreSQL.")
    if not DATABASE_URL.startswith(("postgres://", "postgresql://")):
        raise ImproperlyConfigured("DATABASE_URL must use PostgreSQL; local SQLite uses SACRATISSIMUM_DB_PATH.")
    DATABASES["default"] = dj_database_url.parse(DATABASE_URL, conn_max_age=60)
    if not DEBUG:
        # Encrypt AND verify the PostgreSQL server certificate/hostname.
        # A provider-specific CA may be supplied as a private runtime file.
        options = DATABASES["default"].setdefault("OPTIONS", {})
        options["sslmode"] = "verify-full"
        options.setdefault("sslrootcert", os.environ.get("PGSSLROOTCERT", "system"))

EMAIL_HOST = os.environ.get("EMAIL_HOST", "")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "true").lower() == "true"
EMAIL_USE_SSL = os.environ.get("EMAIL_USE_SSL", "false").lower() == "true"
if EMAIL_USE_SSL:
    EMAIL_USE_TLS = False
EMAIL_TIMEOUT = 10
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "webmaster@localhost" if DEBUG else "")
EMAIL_BACKEND = ("django.core.mail.backends.console.EmailBackend" if DEBUG
                 else "django.core.mail.backends.smtp.EmailBackend" if EMAIL_HOST
                 else "django.core.mail.backends.dummy.EmailBackend")
SITE_URL = os.environ.get("SITE_URL", f"https://{RENDER_HOSTNAME}" if RENDER_HOSTNAME else "http://127.0.0.1:8000").rstrip("/")
if not DEBUG and SITE_URL and not SITE_URL.startswith("https://"):
    # A disabled preview without a host can still run build-time checks.
    if RENDER_HOSTNAME or DATABASE_URL:
        raise ImproperlyConfigured("Production SITE_URL must use HTTPS.")

ACCOUNTS_ENABLED = os.environ.get("ACCOUNTS_ENABLED", "true" if DEBUG else "false").lower() == "true"
STORE_FEATURES_ENABLED = bool(not PREVIEW_MODE and ACCOUNTS_ENABLED and (DEBUG or (DATABASE_URL and EMAIL_HOST and DEFAULT_FROM_EMAIL)))
LOGIN_URL = "commerce:login"
LOGIN_REDIRECT_URL = "commerce:account"
LOGOUT_REDIRECT_URL = "store:home"
PASSWORD_RESET_TIMEOUT = 3600
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
AUTHENTICATION_BACKENDS = ["axes.backends.AxesStandaloneBackend", "django.contrib.auth.backends.ModelBackend"]
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = timedelta(minutes=15)
AXES_LOCKOUT_PARAMETERS = [["username", "ip_address"]]
AXES_RESET_ON_SUCCESS = True
AXES_VERBOSE = False
AXES_LOCKOUT_TEMPLATE = "commerce/locked.html"
ADMIN_REQUIRE_OTP = not DEBUG

STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
# This implementation is test-mode only. No live charges can be enabled accidentally.
if STRIPE_SECRET_KEY and not STRIPE_SECRET_KEY.startswith(("sk_test_", "rk_test_")):
    raise ImproperlyConfigured("Only Stripe TEST-mode keys are supported in this version.")
CHECKOUT_ENABLED = os.environ.get("CHECKOUT_ENABLED", "false").lower() == "true"
STORE_CURRENCY = "usd"
STORE_FULFILLMENT = os.environ.get("STORE_FULFILLMENT", "shipping")  # shipping or pickup; owner must confirm.
SHIPPING_COUNTRIES = [c.strip().upper() for c in os.environ.get("SHIPPING_COUNTRIES", "US").split(",") if c.strip()]
SHIPPING_RATE_CENTS = int(os.environ.get("SHIPPING_RATE_CENTS", "-1"))
PICKUP_INSTRUCTIONS = os.environ.get("PICKUP_INSTRUCTIONS", "")
STRIPE_AUTOMATIC_TAX = True
DATA_UPLOAD_MAX_MEMORY_SIZE = 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024

# Optional S3-compatible durable product-media storage. No service is provisioned.
STORAGE_BUCKET = os.environ.get("STORAGE_BUCKET", "")
if STORAGE_BUCKET:
    endpoint = os.environ.get("STORAGE_ENDPOINT_URL", "")
    if not endpoint or not os.environ.get("STORAGE_ACCESS_KEY") or not os.environ.get("STORAGE_SECRET_KEY"):
        raise ImproperlyConfigured("Object storage requires an explicit endpoint and private access credentials.")
    if endpoint and not endpoint.startswith("https://"):
        raise ImproperlyConfigured("Object storage must use HTTPS.")
    STORAGES["default"] = {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            "bucket_name": STORAGE_BUCKET,
            "access_key": os.environ.get("STORAGE_ACCESS_KEY", ""),
            "secret_key": os.environ.get("STORAGE_SECRET_KEY", ""),
            "endpoint_url": endpoint or None,
            "region_name": os.environ.get("STORAGE_REGION", "us-east-1"),
            "default_acl": None, "file_overwrite": False, "querystring_auth": True,
        },
    }

DEFAULT_EXCEPTION_REPORTER_FILTER = "commerce.reporting.PrivateExceptionReporterFilter"

OTP_TOTP_ISSUER = "Sacratissimum"
