import asyncio
from typing import Dict, Tuple, get_args

from django.core.management.base import BaseCommand
from django.db import transaction

from investors.management.quotes_io import fetch_quotes_async
from investors.management.utils.timer import timer
from investors.management.utils.types_and_enums import Source
from investors.models import Asset


def collect_to_update(quotes, assets_by_id):
    to_update = []
    for aid, (p, v) in quotes.items():
        asset = assets_by_id[aid]
        if not asset:
            continue
        changed = False
        if p != asset.price:
            asset.price = p
            changed = True
        if v != asset.volatility:
            asset.volatility = v
            changed = True
        if changed:
            to_update.append(asset)
    return to_update


class Command(BaseCommand):
    help = "Fetch asset quotes concurrently (asyncio) and bulk-update Assets."

    def add_arguments(self, parser):
        parser.add_argument("--source", choices=list(get_args(Source)), default="demo")
        parser.add_argument("--concurrency", type=int, default=50)

    def handle(self, *args, **opts):
        source = opts["source"]
        concurrency = opts["concurrency"]

        self.stdout.write(self.style.NOTICE("Loading assets (id, name)…"))
        id_and_ticker = [(a.id, a.name) for a in Asset.objects.all()]
        if not id_and_ticker:
            self.stdout.write(self.style.WARNING("No assets found. Seed first."))
            return

        self.stdout.write(
            self.style.NOTICE(
                f"Fetching quotes (source={source}, concurrency={concurrency})…"
            )
        )

        with timer("Async fetch"):
            quotes: Dict[int, Tuple[float, float]] = asyncio.run(
                fetch_quotes_async(id_and_ticker, source, concurrency)
            )
        self.stdout.write(self.style.SUCCESS(f"Fetched {len(quotes)} quotes."))

        ids = quotes.keys()
        assets_by_id = Asset.objects.in_bulk(ids)
        if not assets_by_id:
            self.stdout.write(
                self.style.WARNING("No matching assets for returned quotes.")
            )
            return
        to_update = collect_to_update(quotes, assets_by_id)
        if not to_update:
            self.stdout.write("Quotes identical to current values. Nothing to update.")
            return

        with transaction.atomic():
            Asset.objects.bulk_update(
                to_update, ["price", "volatility"], batch_size=500
            )
        self.stdout.write(self.style.SUCCESS(f"Updated {len(to_update)} assets."))
