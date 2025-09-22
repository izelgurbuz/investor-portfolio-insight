from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


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
        #         added a (portfolio, asset) index to speed up queries that filter by both fields together, and a separate asset index to optimize queries that filter only by asset.
        # Without these, the database would scan every row because it only has default indexes on primary keys, not on these filter fields.
        indexes = [
            models.Index(
                fields=["portfolio", "asset"], name="idx_position_portfolio_asset"
            ),
            models.Index(fields=["asset"], name="idx_position_asset"),
        ]

    def __str__(self) -> str:
        return f"Position(p={self.portfolio_id}, a={self.asset_id}, q={self.quantity}, px={self.avg_price})"


class EODPrice(models.Model):
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE)
    date = models.DateField()
    close = models.DecimalField(max_digits=18, decimal_places=6)
    volume = models.BigIntegerField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["asset", "date"], name="uniq_asset_date")
        ]
        indexes = [
            models.Index(fields=["asset", "-date"]),
            models.Index(fields=["date"]),
        ]


class Earnings(models.Model):
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE)
    period_end = models.DateField()  # quarter end
    eps = models.DecimalField(max_digits=18, decimal_places=6)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["asset", "period_end"], name="uniq_asset_period"
            )
        ]
        indexes = [models.Index(fields=["asset", "-period_end"])]


class PortfolioStat(models.Model):
    portfolio = models.OneToOneField(
        "Portfolio", on_delete=models.CASCADE, related_name="stat", primary_key=True
    )
    port_vol = models.FloatField(null=True, blank=True)
    sharpe_proxy = models.FloatField(null=True, blank=True)
    updated_at = models.DateTimeField(default=timezone.now)

    def __str__(self) -> str:
        return f"PortfolioStat(p={self.portfolio_id}, vol={self.port_vol}, sharpe={self.sharpe_proxy})"
