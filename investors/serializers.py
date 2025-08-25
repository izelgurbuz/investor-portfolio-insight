from rest_framework import serializers

from .models import Asset, Investor, InvestorProfile, Portfolio


class InvestorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Investor
        fields = "__all__"


class InvestorProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvestorProfile
        fields = "__all__"


class AssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Asset
        fields = "__all__"


class PortfolioDetailSerializer(serializers.ModelSerializer):
    # these fields exist at render time
    asset_count = serializers.IntegerField(read_only=True)
    port_vol = serializers.FloatField(read_only=True, allow_null=True)
    sharpe_proxy = serializers.FloatField(read_only=True, allow_null=True)
    assets = AssetSerializer(many=True, read_only=True)

    class Meta:
        model = Portfolio
        fields = (
            "id",
            "name",
            "investor",
            "asset_count",
            "port_vol",
            "sharpe_proxy",
            "assets",
        )


class PortfolioSummarySerializer(serializers.ModelSerializer):
    # these fields exist at render time
    asset_count = serializers.IntegerField(read_only=True)
    port_vol = serializers.FloatField(read_only=True, allow_null=True)
    sharpe_proxy = serializers.FloatField(read_only=True, allow_null=True)

    class Meta:
        model = Portfolio
        fields = ("id", "name", "asset_count", "port_vol", "sharpe_proxy")
