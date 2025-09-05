# core/health.py
from __future__ import annotations
from django.http import JsonResponse
from django.db import connection
from django.conf import settings

def health_view(_request):
    return JsonResponse({"status": "ok"})

def ready_view(_request):
    ok = True
    checks = {}

    # DB check
    try:
        with connection.cursor() as cur:
            cur.execute("SELECT 1;")
            checks["db"] = "ok"
    except Exception as e:
        checks["db"] = f"err:{e}"
        ok = False

    # Redis check (broker)
    try:
        import redis
        r = redis.from_url(getattr(settings, "REDIS_URL", "redis://localhost:6379/0"))
        r.ping()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"err:{e}"
        ok = False

    return JsonResponse({"ready": ok, "checks": checks}, status=200 if ok else 503)
