from typing import get_args

from django.core.management.base import BaseCommand
from django.db import transaction

from investors.management.threaded_fetch import fetch_quotes_threaded
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
        parser.add_argument("--max-workers", type=int, default=50)

    def handle(self, *args, **opts):
        source = opts["source"]
        max_workers = opts["max_workers"]

        self.stdout.write(self.style.NOTICE("Loading assets (id, name)…"))
        asset_list = list(Asset.objects.only("id", "name"))
        if not asset_list:
            self.stdout.write(self.style.WARNING("No assets found. Seed first."))
            return
        aid_and_tkr = [(a.id, a.name) for a in asset_list]

        self.stdout.write(
            self.style.NOTICE(
                f"Fetching quotes with threads (source={source}, workers={max_workers})…"
            )
        )

        with timer("Threaded fetch"):
            quotes = fetch_quotes_threaded(aid_and_tkr, source, max_workers)
        self.stdout.write(self.style.SUCCESS(f"Fetched {len(quotes)} quotes."))
        print(quotes)
        ids = quotes.keys()
        assets_by_id = Asset.objects.in_bulk(ids)
        if not assets_by_id:
            self.stdout.write(
                self.style.WARNING("No matching assets for returned quotes.")
            )
            return
        to_update = collect_to_update(quotes, assets_by_id)
        with transaction.atomic():
            if to_update:
                Asset.objects.bulk_update(
                    to_update, ["price", "volatility"], batch_size=500
                )
        self.stdout.write(self.style.SUCCESS(f"Updated {len(to_update)} assets."))
