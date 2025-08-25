import os
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

load_dotenv()  # loads .env into environment

ALPHAVANTAGE_API_KEY = os.getenv("ALPHAVANTAGE_API_KEY")

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = "django-insecure-placeholder"

DEBUG = True

ALLOWED_HOSTS = []

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "django_filters",
    "investors",
]
REST_FRAMEWORK = {
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.LimitOffsetPagination",
    "PAGE_SIZE": 20,
}

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "core.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
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

WSGI_APPLICATION = "core.wsgi.application"


def _pg_from_env():
    url = os.environ.get("DATABASE_URL")
    if url:
        u = urlparse(url)
        return {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": u.path.lstrip("/"),
            "USER": u.username,
            "PASSWORD": u.password,
            "HOST": u.hostname,
            "PORT": u.port or "5432",
        }
    host = os.environ.get("POSTGRES_HOST")
    if host:
        return {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("POSTGRES_DB", "finance"),
            "USER": os.environ.get("POSTGRES_USER", "finance"),
            "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "finance"),
            "HOST": host,
            "PORT": os.environ.get("POSTGRES_PORT", "5432"),
        }
    return None


_pg = _pg_from_env()

DATABASES = {
    "default": _pg
    or {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
