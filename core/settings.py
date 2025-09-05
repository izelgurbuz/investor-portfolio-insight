import os
from pathlib import Path
from urllib.parse import urlparse

from celery.schedules import crontab
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

# ---- Celery / Redis ----
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
CELERY_IMPORTS = ("investors.tasks",)
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_TASK_ALWAYS_EAGER = False  # True only for unit tests if desired
CELERY_TASK_TIME_LIMIT = 60
CELERY_TASK_SOFT_TIME_LIMIT = 50
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True

# ---- OpenAPI / DRF schema ----
INSTALLED_APPS += ["drf_spectacular"]
REST_FRAMEWORK.update(
    {
        "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    }
)
SPECTACULAR_SETTINGS = {
    "TITLE": "Investor Portfolio API",
    "DESCRIPTION": "Finance-grade backend with async fetch, analytics, bulk ops, and tasks.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

# ---- Logging (simple structured) ----
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "format": '{"ts":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","msg":"%(message)s"}',
        },
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "json"},
    },
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "celery": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "django.request": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

CELERY_TIMEZONE = os.getenv("CELERY_TIMEZONE", "Europe/London")
SCHEDULE_MODE = os.getenv("SCHEDULE_MODE", "interval")  # "interval" or "crontab"

if SCHEDULE_MODE == "interval":
    CELERY_BEAT_SCHEDULE = {
        "recompute-interval": {
            "task": "investors.tasks.nightly_recompute_all_portfolios",
            "schedule": float(
                os.getenv("RECOMPUTE_INTERVAL_SEC", "86400")
            ),  # default 24h
        },
    }
else:
    CELERY_BEAT_SCHEDULE = {
        "recompute-cron": {
            "task": "investors.tasks.nightly_recompute_all_portfolios",
            "schedule": crontab(
                hour=int(os.getenv("RECOMPUTE_HOUR", "2")),
                minute=int(os.getenv("RECOMPUTE_MINUTE", "0")),
            ),
        },
    }
