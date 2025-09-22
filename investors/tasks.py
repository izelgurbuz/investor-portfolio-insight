import logging
import random
import time
from typing import Optional

import redis
from celery import shared_task
from django.conf import settings
from django.utils import timezone

from investors.metrics_services import compute_for_portfolio_id
from investors.models import Portfolio, PortfolioStat

log = logging.getLogger(__name__)
R = redis.from_url(getattr(settings, "REDIS_URL", "redis://localhost:6379/0"))


def _idempotency_key(portfolio_id: int) -> str:
    # key for 1 day
    return f"task:recompute_portfolio_metrics:{portfolio_id}:{timezone.now().date()}"


def _acquire_once(key: str, ttl_sec: int = 86400) -> bool:
    # set key if not exists -> 1 means acquired
    return bool(R.set(key, "1", ex=ttl_sec, nx=True))


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=2,
    retry_backoff_max=30,
    retry_jitter=True,
    max_retries=5,
)
def recompute_portfolio_metrics_task(self, portfolio_id: int) -> Optional[dict]:
    key = _idempotency_key(portfolio_id)
    if not _acquire_once(key, ttl_sec=3600):
        log.info(f"skip: idempotency key exists for portfolio={portfolio_id}")
        return None

    # extra jitter when many tasks start at once
    time.sleep(random.uniform(0.05, 0.25))

    data = compute_for_portfolio_id(portfolio_id)
    if data is None:
        log.warning(f"portfolio {portfolio_id} not found; skipping")
        return None

    obj, _created = PortfolioStat.objects.update_or_create(
        portfolio_id=portfolio_id,
        defaults={
            "port_vol": data["port_vol"],
            "sharpe_proxy": data["sharpe_proxy"],
            "updated_at": timezone.now(),
        },
    )
    log.info(f"updated PortfolioStat p={portfolio_id} data={data}")
    return data


@shared_task(bind=True)
def nightly_recompute_all_portfolios(self, batch_size: int = 200):
    # Fan-out: queue one task per portfolio
    ids = list(Portfolio.objects.values_list("id", flat=True))
    for pid in ids:
        recompute_portfolio_metrics_task.delay(pid)
    return {"queued": len(ids)}


@shared_task(bind=True, name="investors.tasks.debug_sleep")
def debug_sleep(self, seconds: int = 20):
    for _ in range(seconds):
        time.sleep(1)
    return {"slept": seconds, "rand": random.random()}
