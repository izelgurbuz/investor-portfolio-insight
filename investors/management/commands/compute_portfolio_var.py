from django.core.management.base import BaseCommand
from django.db.models import Prefetch

from investors.management.cpu_risk import Position, portfolio_var_parallel
from investors.management.utils.timer import timer
from investors.models import Asset, Portfolio


class Command(BaseCommand):
    help = "Compute 95% VaR for each portfolio using multiprocessing."

    def add_arguments(self, parser):
        parser.add_argument("--paths", type=int, default=30_000)
        parser.add_argument("--max-workers", type=int, default=None)

    def handle(self, *args, **opts):
        paths = opts["paths"]
        max_workers = opts["max_workers"]

        self.stdout.write(self.style.NOTICE("Loading portfolios and assets..."))
        portfolios = Portfolio.objects.prefetch_related(
            Prefetch("assets", queryset=Asset.objects.only("price", "volatility"))
        ).only("id", "assets")
        portfolios_inputs = {}
        for p in portfolios:
            assets = list(p.assets.all())
            if not assets:
                continue
            w = 1.0 / len(assets)
            positions = [
                Position(w, float(a.price or 0.0), float(a.volatility or 0.0))
                for a in assets
            ]
            portfolios_inputs[p.id] = positions

        if not portfolios_inputs:
            self.stdout.write(self.style.WARNING("No portfolios with assets."))
            return
        self.stdout.write(
            self.style.NOTICE(f"Computing VaR in parallel (paths={paths})...")
        )
        with timer("Portfolio VaR computation"):
            var_by_portfolio = portfolio_var_parallel(
                portfolios_inputs, paths=paths, max_workers=max_workers
            )

        lines = ["VaR (95%) by portfolio:"]
        for pid, var_value in sorted(var_by_portfolio.items()):
            lines.append(f"- Portfolio {pid}: VaR ≈ {var_value:,.2f}")
        self.stdout.write(self.style.SUCCESS("\n".join(lines)))
