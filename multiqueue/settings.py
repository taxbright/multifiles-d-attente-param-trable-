"""
Django settings for multiqueue project.
"""
 
from pathlib import Path
import os
from urllib.parse import urlparse, unquote


BASE_DIR = Path(__file__).resolve().parent.parent


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

    # WhiteNoise doit rester juste après SecurityMiddleware.
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

        # Templates globaux éventuels à la racine.
        "DIRS": [
            BASE_DIR / "templates",
        ],

        # Active les templates dans queueapp/templates/queueapp/.
        "APP_DIRS": True,

        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]


WSGI_APPLICATION = "multiqueue.wsgi.application"


def _postgres_from_url(database_url):
    """
    Convertit DATABASE_URL Supabase/PostgreSQL en configuration Django.

    Exemple :
    postgresql://USER:PASSWORD@HOST:PORT/postgres?sslmode=require
    """
    parsed = urlparse(database_url)

    if parsed.scheme not in {"postgres", "postgresql"}:
        raise ValueError(
            "DATABASE_URL doit commencer par postgres:// ou postgresql://"
        )

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


AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


LANGUAGE_CODE = "fr-fr"
TIME_ZONE = "Indian/Antananarivo"

USE_I18N = True
USE_TZ = True


# ==========================
# FICHIERS STATIQUES / DESIGN
# ==========================

STATIC_URL = "/static/"

# Dossier généré automatiquement par collectstatic.
STATIC_ROOT = BASE_DIR / "staticfiles"

# Les fichiers statiques dans queueapp/static/ sont déjà détectés
# grâce à django.contrib.staticfiles.
STATICFILES_DIRS = []

# Si un dossier static/ existe à la racine, on l’ajoute aussi.
ROOT_STATIC_DIR = BASE_DIR / "static"

if ROOT_STATIC_DIR.exists():
    STATICFILES_DIRS.append(ROOT_STATIC_DIR)


STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}


SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")


CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CSRF_TRUSTED_ORIGINS",
        "https://multiqueue.onrender.com,https://*.onrender.com,http://localhost:8000,http://127.0.0.1:8000"
    ).split(",")
    if origin.strip()
]


LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "index"
LOGOUT_REDIRECT_URL = "login"


DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
