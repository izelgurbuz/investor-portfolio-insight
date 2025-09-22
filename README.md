## Investor Portfolio Insight

A hands-on backend project that simulates how a real finance backend works — portfolios, market data, analytics, and background processing.

It’s not a product, but a showcase of modern backend engineering:

- Clean APIs

- Async data fetching

- Background jobs

- Scalable architecture in containers

Everything here is built to look and feel like a real cloud system, just smaller and local.

## What's Inside

API – Django + DRF for portfolios, assets, metrics

Async Fetching – market data updates with retry & backoff

Background Jobs – Celery + Redis for scheduled tasks

Database – Postgres with realistic portfolio models

Monitoring – Flower dashboard to track tasks

Containers – One command brings the whole system up

# 1. Clone
git clone https://github.com/YOUR_USERNAME/investor_portfolio_insight.git
cd investor_portfolio_insight

# 2. Start services
docker compose up --build

# 3. Migrate & seed demo data
export DATABASE_URL=postgres://finance:finance@127.0.0.1:5433/finance
python manage.py migrate
python manage.py seed_portfolio_demo --investors 3 --assets 20

# 4. Explore
# API:    http://localhost:8000/api/
# Flower: http://localhost:5555/


| File                                     | What It Shows                                                          |
| ---------------------------------------- | ---------------------------------------------------------------------- |
| `scripts/threaded_fetch.py`              | Async + multi-threaded API fetching with retries & backoff             |
| `scripts/update_asset_quotes_threads.py` | Bulk database updates with thread pools                                |
| `scripts/compute_portfolio_var.py`       | Portfolio risk simulation (Monte Carlo)                                |
| `scripts/cpu_risk.py`                    | Parallel CPU-bound calculations with multiprocessing                   |
| `investors/tasks.py`                     | Distributed background jobs with Celery                                |
| `investors/views.py`                     | Clean REST API design with Django REST Framework                       |
| `docker-compose.yaml`                    | Cloud-native style service setup (API, DB, Redis, workers, monitoring) |


| Cloud-Native Pattern                                 | Where It’s Practiced                               |
| ---------------------------------------------------- | -------------------------------------------------- |
| **Async I/O** – non-blocking external calls          | `scripts/threaded_fetch.py`                        |
| **Thread pools** – speeding up I/O work              | `scripts/update_asset_quotes_threads.py`           |
| **Process pools** – parallel CPU-bound tasks         | `scripts/cpu_risk.py`                              |
| **Message-driven architecture** – decoupled services | `investors/tasks.py` + `docker-compose.yaml`       |
| **Retry + Backoff** – robust external calls          | `scripts/threaded_fetch.py`                        |
| **Idempotency** – safe repeated operations           | Bulk DB updates (`update_asset_quotes_threads.py`) |
| **Horizontal scaling** – add more workers easily     | `docker-compose.yaml` (`--scale worker=3`)         |
| **Healthchecks & monitoring**                        | Flower + Redis logs                                |
| **Environment-based config** – flexible setups       | `docker-compose.yaml` (env vars for DB, Redis)     |

         ┌─────────────┐
         │  Django API │
         └──────┬──────┘
                │
         ┌──────▼──────┐
         │   Redis     │  (Message Broker)
         └──────┬──────┘
                │
         ┌──────▼──────┐
         │ Celery       │
         │ Workers      │
         └──────┬──────┘
                │
         ┌──────▼──────┐
         │  Postgres    │
         └─────────────┘

