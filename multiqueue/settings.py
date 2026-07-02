"""
Django settings for multiqueue project.
"""

from pathlib import Path
import os
from urllib.parse import urlparse, unquote

BASE_DIR = Path(file).resolve().parent.parent


def _env_bool(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "django-insecure-local-dev-key-change-me"
)

DEBUG = _env_bool("DEBUG", False)

ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv(
        "ALLOWED_HOSTS",
        "localhost,127.0.0.1,testserver,.onrender.com,multiqueue.onrender.com"
    ).split(",")
    if host.strip()
]


INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "queueapp",
]


MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",

    # Important : WhiteNoise doit être juste après SecurityMiddleware
    "whitenoise.middleware.WhiteNoiseMiddleware",

    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


ROOT_URLCONF = "multiqueue.urls"


TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",

        # Important si tu as un dossier templates/ à la racine
        "DIRS": [
            BASE_DIR / "templates",
        ],

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


WSGI_APPLICATION = "multiqueue.wsgi.application"


def _postgres_from_url(database_url):
    parsed = urlparse(database_url)

    if parsed.scheme not in {"postgres", "postgresql"}:
        raise ValueError("DATABASE_URL doit commencer par postgres:// ou postgresql://")

    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": (parsed.path or "/postgres").lstrip("/") or "postgres",
        "USER": unquote(parsed.username or ""),
        "PASSWORD": unquote(parsed.password or ""),
        "HOST": parsed.hostname or "",
        "PORT": str(parsed.port or 5432),
        "OPTIONS": {
            "sslmode": os.getenv("DATABASE_SSLMODE", "require"),
        },
        "CONN_MAX_AGE": int(os.getenv("DATABASE_CONN_MAX_AGE", "0")),
    }


DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
USE_SUPABASE = _env_bool("USE_SUPABASE", False) or bool(DATABASE_URL)

if USE_SUPABASE:
    if DATABASE_URL:
        DATABASES = {
            "default": _postgres_from_url(DATABASE_URL)
        }
    else:
        DATABASES = {
            "default": {
                "ENGINE": "django.db.backends.postgresql",
                "NAME": os.getenv("SUPABASE_DB_NAME", "postgres"),
                "USER": os.getenv("SUPABASE_DB_USER", "postgres"),
                "PASSWORD": os.getenv("SUPABASE_DB_PASSWORD", ""),
                "HOST": os.getenv("SUPABASE_DB_HOST", ""),
                "PORT": os.getenv("SUPABASE_DB_PORT", "5432"),
                "OPTIONS": {
                    "sslmode": os.getenv("DATABASE_SSLMODE", "require"),
                },
                "CONN_MAX_AGE": int(os.getenv("DATABASE_CONN_MAX_AGE", "0")),
            }
        }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
