from __future__ import annotations

import threading
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import connection, transaction
from django.db.models import Case, DecimalField, ExpressionWrapper, F, Value, When

from investors.models import Position

DEC = DecimalField(max_digits=20, decimal_places=6)


def buy_safe(portfolio_id: int, asset_id: int, qty: Decimal, price: Decimal) -> None:
    supports_sfu = bool(getattr(connection.features, "has_select_for_update", False))
    with transaction.atomic():
        pos = (
            Position.objects.select_for_update().get(
                portfolio_id=portfolio_id, asset_id=asset_id
            )
            if supports_sfu
            else Position.objects.get(portfolio_id=portfolio_id, asset_id=asset_id)
        )
        num = (F("avg_price") * F("quantity")) + Value(price, output_field=DEC) * Value(
            qty, output_field=DEC
        )
        den = F("quantity") + Value(qty, output_field=DEC)
        new_avg = Case(
            When(den=0, then=F("avg_price")),
            default=ExpressionWrapper(num / den, output_field=DEC),
            output_field=DEC,
        )

        Position.objects.filter(id=pos.id).update(
            quantity=den,
            avg_price=new_avg,
        )


def buy_unsafe(portfolio_id: int, asset_id: int, qty: Decimal, price: Decimal) -> None:
    with transaction.atomic():
        pos = Position.objects.get(portfolio_id=portfolio_id, asset_id=asset_id)
        old_q, old_px = pos.quantity, pos.avg_price
        new_q = old_q + qty
        new_px = (old_px * old_q + price * qty) / (new_q or 1)
        pos.quantity = new_q
        pos.avg_price = new_px
        pos.save()


class Command(BaseCommand):
    help = "Simulate two concurrent buys: it shows row locks on Postgres (safe) vs lost update (--unsafe)."

    def add_arguments(self, parser):
        parser.add_argument("--portfolio-id", type=int, required=True)
        parser.add_argument("--asset-id", type=int, required=True)
        parser.add_argument("--qty", type=str, default="10")
        parser.add_argument("--price", type=str, default="100.0")
        parser.add_argument("--unsafe", action="store_true")

    def handle(self, *args, **opts):
        pid, aid = opts["portfolio_id"], opts["asset_id"]
        qty, price = Decimal(opts["qty"]), Decimal(opts["price"])

        Position.objects.get_or_create(portfolio_id=pid, asset_id=aid)
        Position.objects.filter(portfolio_id=pid, asset_id=aid).update(
            quantity=0, avg_price=0
        )

        fn = buy_unsafe if opts["unsafe"] else buy_safe
        t1 = threading.Thread(target=fn, args=(pid, aid, qty, price))
        t2 = threading.Thread(target=fn, args=(pid, aid, qty, price))
        t1.start()
        t2.start()
        t1.join()
        t2.join()
        pos = Position.objects.get(portfolio_id=pid, asset_id=aid)
        self.stdout.write(
            self.style.SUCCESS(
                f"qty={pos.quantity} avg_price={pos.avg_price} (backend={connection.vendor}, unsafe={opts['unsafe']})"
            )
        )
