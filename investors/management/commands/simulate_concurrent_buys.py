import threading
import time
from decimal import Decimal
from typing import Dict, List, Tuple

from django.core.management.base import BaseCommand
from django.db import connection, transaction
from django.db.models import Case, DecimalField, ExpressionWrapper, F, Q, Value, When

from investors.models import Position

DEC = DecimalField(max_digits=20, decimal_places=6)

Pair = Tuple[int, int]  # (portfolio_id, asset_id)


def _q_for_pairs(pairs: List[Pair]):
    q = Q()
    for pid, aid in pairs:
        q |= Q(portfolio=pid, asset=aid)
    return q


def calculate_new_values(pos: Position, qty: Decimal, price: Decimal):
    old_q, old_px = pos.quantity, pos.avg_price
    new_q = old_q + qty
    new_px = (old_px * old_q + price * qty) / (new_q or 1)
    return new_q, new_px


def buy_unsafe_one(pid: int, aid: int, qty: Decimal, price: Decimal) -> None:
    """
    Classic lost/update demo. Do NOT use in production.
    """
    with transaction.atomic():
        pos = Position.objects.get(portfolio_id=pid, asset_id=aid)
        # Artificial delay to amplify the race window
        time.sleep(0.1)
        new_q, new_px = calculate_new_values(pos, qty, price)
        Position.objects.filter(pk=pos.pk).update(quantity=new_q, avg_price=new_px)


def buy_safe_one(pid: int, aid: int, qty: Decimal, price: Decimal) -> None:
    """
    Same as unsafe but with select_for_update() to serialize writers.
    """
    with transaction.atomic():
        pos = Position.objects.select_for_update().get(portfolio_id=pid, asset_id=aid)
        time.sleep(0.1)
        new_q, new_px = calculate_new_values(pos, qty, price)
        Position.objects.filter(pk=pos.pk).update(quantity=new_q, avg_price=new_px)


def buy_set_based_pairs(payload: Dict[Pair, Tuple[Decimal, Decimal]]) -> None:
    """
    still atomically and safely, without Python read/compute gaps.
    We iterate rows but each UPDATE uses F() math (atomic in DB).
    """
    if not payload:
        return

    q = _q_for_pairs(list(payload.keys()))

    with transaction.atomic():
        rows = (
            Position.objects.filter(q)
            .order_by("portfolio_id", "asset_id")
            .only("id", "portfolio_id", "asset_id")
        )

        for pos in rows:
            qty, price = payload[(pos.portfolio_id, pos.asset_id)]
            num = F("avg_price") * F("quantity") + Value(
                price, output_field=DEC
            ) * Value(qty, output_field=DEC)
            den = F("quantity") + Value(qty, output_field=DEC)
            updated = Position.objects.filter(pk=pos.pk).update(
                avg_price=Case(
                    When(quantity=0, then=Value(price, output_field=DEC)),
                    default=ExpressionWrapper(num / den, output_field=DEC),
                    output_field=DEC,
                ),
                quantity=ExpressionWrapper(den, output_field=DEC),
            )
            assert updated == 1, (
                f"Expected 1 row updated, got {updated} for pos={pos.pk}"
            )


def buy_safe_pairs(
    payload: Dict[Pair, Tuple[Decimal, Decimal]], skip_locked: bool = False
) -> None:
    """
    Lock the exact rows first then do per row read/compute/write safely.
    Use this when business logic MUST read values in Python first.
    """
    if not payload:
        return

    q = _q_for_pairs(list(payload.keys()))
    supports_sfu = bool(getattr(connection.features, "has_select_for_update", False))

    with transaction.atomic():
        qs = (
            Position.objects.filter(q)
            .order_by("portfolio_id", "asset_id")
            .only("id", "portfolio_id", "asset_id", "quantity", "avg_price")
        )
        if supports_sfu:
            qs = qs.select_for_update(skip_locked=skip_locked)

        for pos in qs:
            qty, price = payload[(pos.portfolio_id, pos.asset_id)]
            new_q, new_px = calculate_new_values(pos, qty, price)
            updated = Position.objects.filter(pk=pos.pk).update(
                quantity=new_q, avg_price=new_px
            )
            assert updated == 1, (
                f"Expected 1 row updated, got {updated} for pos={pos.pk}"
            )


class Command(BaseCommand):
    help = "Demonstrate unsafe vs safe vs set-based position updates with threads."

    def add_arguments(self, parser):
        parser.add_argument("--mode", choices=["unsafe", "safe", "set"], default="safe")
        # Small demo universe: (1,1), (1,2), (2,1), (2,2)
        parser.add_argument("--qty1", default="1")
        parser.add_argument("--qty2", default="1")

    def handle(self, *args, **opts):
        mode = opts["mode"]
        qty1 = Decimal(opts["qty1"])
        qty2 = Decimal(opts["qty2"])

        # Seed 4 positions
        pairs: List[Pair] = [(1, 1), (1, 2), (2, 1), (2, 2)]
        for pid, aid in pairs:
            Position.objects.get_or_create(portfolio_id=pid, asset_id=aid)
            Position.objects.filter(portfolio_id=pid, asset_id=aid).update(
                quantity=Decimal("1"), avg_price=Decimal("10")
            )

        self.stdout.write(
            self.style.WARNING(f"Backend={connection.vendor}, mode={mode}")
        )

        if mode == "unsafe":
            # Two threads hit SAME row to show lost update
            t1 = threading.Thread(
                target=buy_unsafe_one, args=(1, 1, qty1, Decimal("20"))
            )
            t2 = threading.Thread(
                target=buy_unsafe_one, args=(1, 1, qty2, Decimal("40"))
            )
            t1.start()
            t2.start()
            t1.join()
            t2.join()

        elif mode == "safe":
            # Same scenario but safe with row lock
            t1 = threading.Thread(target=buy_safe_one, args=(1, 1, qty1, Decimal("20")))
            t2 = threading.Thread(target=buy_safe_one, args=(1, 1, qty2, Decimal("40")))
            t1.start()
            t2.start()
            t1.join()
            t2.join()

        elif mode == "set":
            # Per row different qty/price applied atomically with F() math
            payload1: Dict[Pair, Tuple[Decimal, Decimal]] = {
                (1, 1): (Decimal("1"), Decimal("20")),
                (1, 2): (Decimal("1"), Decimal("40")),
                (2, 1): (Decimal("1"), Decimal("60")),
                (2, 2): (Decimal("1"), Decimal("80")),
            }
            payload2: Dict[Pair, Tuple[Decimal, Decimal]] = {
                (1, 1): (Decimal("1"), Decimal("10")),
                (1, 2): (Decimal("2"), Decimal("10")),
                (2, 1): (Decimal("3"), Decimal("10")),
                (2, 2): (Decimal("4"), Decimal("10")),
            }
            t1 = threading.Thread(target=buy_set_based_pairs, args=(payload1,))
            t2 = threading.Thread(target=buy_set_based_pairs, args=(payload2,))
            t1.start()
            t2.start()
            t1.join()
            t2.join()

        for pos in Position.objects.filter(
            portfolio_id__in=[1, 2], asset_id__in=[1, 2]
        ).order_by("portfolio_id", "asset_id"):
            self.stdout.write(
                self.style.SUCCESS(
                    f"(pid={pos.portfolio_id}, aid={pos.asset_id}) qty={pos.quantity} avg={pos.avg_price}"
                )
            )
