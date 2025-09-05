import queue
import threading
import uuid
from decimal import Decimal
from typing import TypedDict

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import DecimalField, ExpressionWrapper, F, Value

from investors.models import Position

DEC = DecimalField(max_digits=20, decimal_places=6)


class OrderMsg(TypedDict):
    portfolio_id: int
    asset_id: int
    qty: Decimal
    price: Decimal
    order_id: str


def process_order(msg: OrderMsg) -> None:
    pid, aid, qty, price = (
        msg["portfolio_id"],
        msg["asset_id"],
        msg["qty"],
        msg["price"],
    )
    Position.objects.get_or_create(asset=aid, portfolio=pid)
    with transaction.atomic():
        num = F("quantity") * F("avg_price") + Value(qty, output_field=DEC) * Value(
            price, output_field=DEC
        )
        den = F("quantity") + Value(qty, output_field=DEC)
        new_avg = ExpressionWrapper(num / den, output_field=DEC)
        Position.objects.filter(asset=aid, portfolio=pid).update(
            avg_price=new_avg, quantity=den
        )


def worker(q: queue.Queue[OrderMsg]):
    while True:
        msg = q.get()
        try:
            process_order(msg)
        finally:
            q.task_done()


class Command(BaseCommand):
    """
    It’s a mini version of what a trading system or stock broker backend might do
    when handling many incoming orders at the same time.
    queue.Queue ensures thread-safe communication between producer and worker threads
    """

    help = "Apply buy orders concurrently via a simple in-process queue."

    def add_arguments(self, parser):
        parser.add_argument("--portfolio-id", type=int, required=True)
        parser.add_argument("--asset-id", type=int, required=True)
        parser.add_argument("--orders", type=int, default=200)
        parser.add_argument("--workers", type=int, default=8)
        parser.add_argument("--qty", type=str, default="1")
        parser.add_argument("--price", type=str, default="100.0")

    def handle(self, *args, **opts):
        pid, aid = opts["portfolio_id"], opts["asset_id"]
        N, W = opts["orders"], opts["workers"]
        qty, price = Decimal(opts["qty"]), Decimal(opts["price"])

        q: queue.Queue[OrderMsg] = queue.Queue(maxsize=1000)  # backpressure
        threads = [
            threading.Thread(target=worker, args=(q,), daemon=True) for _ in range(W)
        ]
        for t in threads:
            t.start()
        for _ in range(N):
            q.put(
                OrderMsg(
                    portfolio_id=pid,
                    asset_id=aid,
                    qty=qty,
                    price=price,
                    order_id=str(uuid.uuid4()),
                )
            )
        q.join()
        pos = Position.objects.get(portfolio_id=pid, asset_id=aid)
        self.stdout.write(
            self.style.SUCCESS(
                f"Applied {N} orders with W={W}: qty={pos.quantity}, avg_price={pos.avg_price}"
            )
        )
