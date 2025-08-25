from random import randint, sample

from django.core.management.base import BaseCommand
from django.db import transaction

from investors.models import Asset, Investor, InvestorProfile, Portfolio

ASSET_NAMES = [
    "NVIDIA",
    "Tesla",
    "Apple",
    "AAPL",
    "MSFT",
    "GOOGL",
    "AMZN",
    "META",
    "TSLA",
    "NVDA",
    "ORCL",
    "ADBE",
    "INTC",
    "AMD",
    "IBM",
]


class Command(BaseCommand):
    help = "Seed demo investors, assets, and portfolios."

    def add_arguments(self, parser):
        parser.add_argument("--investors", type=int, default=3)
        parser.add_argument("--assets", type=int, default=len(ASSET_NAMES))
        parser.add_argument("--max-assets-per-portfolio", type=int, default=8)

    @transaction.atomic
    def handle(self, *args, **opts):
        inv_num = opts["investors"]
        a_num = opts["assets"]
        max_assets_per_portfolio = opts["max_assets_per_portfolio"]

        assets = []
        for i in range(min(a_num, len(ASSET_NAMES))):
            asset, _ = Asset.objects.update_or_create(
                name=ASSET_NAMES[i],
                defaults={"category": "Equity", "price": 0, "volatility": 0.0},
            )
            assets.append(asset)

        for i in range(inv_num):
            investor, _ = Investor.objects.update_or_create(
                email=f"investor{i}@gmail.com", defaults={"name": f"investor{i}"}
            )
            InvestorProfile.objects.update_or_create(
                investor=investor,
                defaults={
                    "risk_tolerance": "medium",
                    "experience_level": "Intermediate",
                },
            )
            cap = min(max_assets_per_portfolio, len(assets))

            num_ports = randint(1, 3)  # 1..3
            portfolios = []
            for j in range(1, num_ports + 1):
                name = f"{investor.name}-Portfolio-{j}"
                # create (or get_or_create with name in lookup if you expect reruns)
                p = Portfolio.objects.create(investor=investor, name=name)

                k = randint(4, cap)  # how many assets
                chosen = sample(list(assets), k)  # unique picks, no collisions
                p.assets.set(chosen)  # replaces to exactly this set
                portfolios.append(p)
        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {inv_num} investors, {a_num} assets, and portfolios."
            )
        )
