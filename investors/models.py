from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models


class Investor(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)


class InvestorProfile(models.Model):
    investor = models.OneToOneField(Investor, on_delete=models.CASCADE)
    risk_tolerance = models.CharField(max_length=50)
    experience_level = models.CharField(max_length=50)


class Asset(models.Model):
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=50)
    price = models.FloatField()
    volatility = models.FloatField()


class Portfolio(models.Model):
    investor = models.ForeignKey(Investor, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    assets = models.ManyToManyField(Asset, related_name="portfolios")


class Position(models.Model):
    portfolio = models.ForeignKey(
        "Portfolio", on_delete=models.CASCADE, related_name="positions", db_index=True
    )
    asset = models.ForeignKey(
        "Asset", on_delete=models.CASCADE, related_name="positions", db_index=True
    )
    quantity = models.DecimalField(
        max_digits=20,
        decimal_places=6,
        default=Decimal("0"),
        validators=[MinValueValidator(0)],
    )
    avg_price = models.DecimalField(
        max_digits=20, decimal_places=6, default=Decimal("0")
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["portfolio", "asset"], name="uniq_position_portfolio_asset"
            ),
            models.CheckConstraint(
                check=models.Q(quantity__gte=0), name="chk_position_quantity_nonneg"
            ),
        ]
        indexes = [
            models.Index(
                fields=["portfolio", "asset"], name="idx_position_portfolio_asset"
            ),
            models.Index(fields=["asset"], name="idx_position_asset"),
        ]

    def __str__(self) -> str:
        return f"Position(p={self.portfolio_id}, a={self.asset_id}, q={self.quantity}, px={self.avg_price})"
