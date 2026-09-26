"""
Greensheet prototype settings.

One process, one SQLite file, outbound email via SMTP. In development the
email backend prints to the console and magic links are also shown on screen.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = Path(os.environ.get("GREENSHEET_DATA", BASE_DIR / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

DEBUG = os.environ.get("GREENSHEET_DEBUG", "1") == "1"
ALLOWED_HOSTS = ["*"]


def _secret_key():
    """From the environment, else a key generated once and kept in the data dir."""
    if os.environ.get("GREENSHEET_SECRET_KEY"):
        return os.environ["GREENSHEET_SECRET_KEY"]
    f = DATA_DIR / "secret_key"
    if f.exists():
        return f.read_text().strip()
    from django.core.management.utils import get_random_secret_key

    key = get_random_secret_key()
    f.write_text(key)
    try:
        f.chmod(0o600)
    except OSError:
        pass
    return key


SECRET_KEY = _secret_key()

# Public URL of this instance. Used in emails, QR codes, and hard copies.
SITE_URL = os.environ.get("GREENSHEET_SITE_URL", "http://localhost:8000").rstrip("/")
CSRF_TRUSTED_ORIGINS = [SITE_URL]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "sheets",
]

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
                "sheets.context.site",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.environ.get("GREENSHEET_DB", DATA_DIR / "greensheet.sqlite3"),
        "OPTIONS": {"timeout": 20, "init_command": "PRAGMA journal_mode=WAL;"},
    }
}

AUTH_USER_MODEL = "sheets.Person"
LOGIN_URL = "/signin"

# Sessions are long lived and per device. A person signs in again on a new
# device by asking for another magic link.
SESSION_COOKIE_AGE = 60 * 60 * 24 * 90
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"

MAGIC_LINK_TTL_MINUTES = 15
DAILY_INVITE_CAP = 20

LANGUAGE_CODE = "en-us"
TIME_ZONE = os.environ.get("GREENSHEET_TZ", "UTC")
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Email. Every message is from the same sender name and address.
DEFAULT_FROM_EMAIL = os.environ.get("GREENSHEET_FROM_EMAIL", "Greensheet <sheets@localhost>")
if os.environ.get("GREENSHEET_SMTP_HOST"):
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = os.environ["GREENSHEET_SMTP_HOST"]
    EMAIL_PORT = int(os.environ.get("GREENSHEET_SMTP_PORT", "587"))
    EMAIL_HOST_USER = os.environ.get("GREENSHEET_SMTP_USER", "")
    EMAIL_HOST_PASSWORD = os.environ.get("GREENSHEET_SMTP_PASSWORD", "")
    EMAIL_USE_TLS = os.environ.get("GREENSHEET_SMTP_TLS", "1") == "1"
else:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# In DEBUG, magic links are also shown on the page so the prototype can be
# used without reading the console.
SHOW_MAGIC_LINKS = DEBUG
