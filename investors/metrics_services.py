from typing import Dict, Optional

from django.db.models import (
    Case,
    Count,
    ExpressionWrapper,
    F,
    FloatField,
    Sum,
    Value,
    When,
)
from django.db.models.functions import Coalesce, Sqrt

from investors.models import Portfolio


def annotate_metrics(qs):
    """
    Portfolio metrics:
      - asset_count: number of assets in the portfolio
      - port_vol:    rough portfolio volatility proxy (sum of vol^2)^(1/2) / count
      - sharpe_proxy: 1 / port_vol (only when port_vol > 0)
    """
    qs_annotated = (
        qs.annotate(
            asset_count=Count(
                "assets", distinct=True
            ),  # m2m relations can bring duplicates in the table
            sum_var=Coalesce(
                Sum(
                    F("assets__volatility") * F("assets__volatility"),
                    output_field=FloatField(),
                ),
                Value(0.0),
            ),
        )
        .annotate(
            port_vol=Case(
                When(
                    asset_count__gt=0,
                    then=ExpressionWrapper(
                        Sqrt(F("sum_var")) / F("asset_count"), output_field=FloatField()
                    ),
                ),
                default=Value(None, output_field=FloatField()),
                output_field=FloatField(),
            )
        )
        .annotate(
            sharpe_proxy=Case(
                When(
                    port_vol__gt=0,
                    then=ExpressionWrapper(
                        Value(1.0) / F("port_vol"), output_field=FloatField()
                    ),
                ),
                default=Value(None, output_field=FloatField()),
                output_field=FloatField(),
            )
        )
        .annotate(total_value=Sum(F("positions__quantity") * F("positions__avg_price")))
    )
    return qs_annotated


def compute_for_portfolio_id(portfolio_id: int) -> Optional[Dict[str, float]]:
    qs = annotate_metrics(Portfolio.objects.filter(id=portfolio_id))
    row = qs.values("port_vol", "sharpe_proxy").first()
    if not row:
        return None
    return {
        "port_vol": float(row["port_vol"]) if row["port_vol"] is not None else None,
        "sharpe_proxy": float(row["sharpe_proxy"])
        if row["sharpe_proxy"] is not None
        else None,
    }


# def portfolio_market_value():
#     portfolio_mv = Portfolio.objects.annotate(
#         total_value=Sum(F("positions__qty") * F("positions__asset__price"))
#     ).values("id", "name", "total_value")
#     return portfolio_mv


# def holder_concentration_per_asset():
#     Asset.objects.annotate(
#         holder=Count("portfolios", distinct=True, total_qty=Sum("positions__qty"))
#     ).values("asset_id", "name", "holders", "total_qty")


# def portfolio_weights(portfolio_id: int):
#     Portfolio.objects.filter(id=portfolio_id).annotate(
#         total_value=Sum(
#             F("positions__qty") * F("positions__asset__price"),
#             output_field=FloatField(),
#         )
#     ).annotate(
#         value_of_this_row=ExpressionWrapper(
#             F("positions__qty") * F("positions__asset__price"),
#             output_field=FloatField(),
#         )
#     ).annotate(
#         weight=ExpressionWrapper(
#             F("value_of_this_row") / F("total_value"), output_field=FloatField()
#         )
#     )
