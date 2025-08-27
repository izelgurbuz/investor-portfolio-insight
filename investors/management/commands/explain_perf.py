from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import connection
from django.db.models import Sum

from investors.models import Portfolio, Position
from investors.views import annotate_metrics


class Command(BaseCommand):
    help = "EXPLAIN/ANALYZE hot queries to validate indexes."

    def handle(self, *args, **opts):
        vendor = connection.vendor
        self.stdout.write(self.style.NOTICE(f"DB vendor: {vendor}"))

        agg_qs = (
            Position.objects.values("portfolio_id")
            .annotate(total_qty=Sum("quantity"))
            .order_by("-total_qty")
        )
        try:
            port_qs = annotate_metrics(Portfolio.objects.all()).order_by(
                "-sharpe_proxy"
            )
        except Exception:
            port_qs = Portfolio.objects.all()

        if vendor == "postgresql":
            self.stdout.write(
                self.style.SUCCESS("Positions aggregation plan (ANALYZE):")
            )
            self.stdout.write(agg_qs.explain(analyze=True, verbose=True))
            self.stdout.write(self.style.SUCCESS("Portfolio metrics plan (ANALYZE):"))
            self.stdout.write(port_qs.explain(analyze=True, verbose=True))
        else:
            with connection.cursor() as cur:
                self.stdout.write(self.style.SUCCESS("Positions aggregation plan:"))
                cur.execute("EXPLAIN QUERY PLAN " + str(agg_qs.query))
                for row in cur.fetchall():
                    self.stdout.write(str(row))
                self.stdout.write(self.style.SUCCESS("Portfolio metrics plan:"))
                cur.execute("EXPLAIN QUERY PLAN " + str(port_qs.query))
                for row in cur.fetchall():
                    self.stdout.write(str(row))
