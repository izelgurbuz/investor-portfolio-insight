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


def annotate_metrics(qs):
    """
    Portfolio metrics:
      - asset_count: number of assets in the portfolio
      - port_vol:    rough portfolio volatility proxy (sum of vol^2)^(1/2) / count
      - sharpe_proxy: 1 / port_vol (only when port_vol > 0)
    """
    qs = (
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
    )
    return qs
