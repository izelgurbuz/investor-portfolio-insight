from django.db import transaction
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
    total_value = serializers.FloatField(read_only=True, allow_null=True)

    class Meta:
        model = Portfolio
        fields = ("id", "name", "asset_count", "port_vol", "sharpe_proxy")


class PortfolioUpsertSerializer(serializers.ModelSerializer):
    investor_email = serializers.EmailField(write_only=True)

    class Meta:
        model = Portfolio
        fields = ("id", "name", "investor_email")
        list_serializer_class = None  # set below

    def validate(self, attrs):
        if not attrs.get("name"):
            raise serializers.ValidationError("name is required")
        return attrs


class PortfolioUpsertListSerializer(serializers.ListSerializer):
    def create(self, validated_data):
        # validated_data: list of dicts
        created_or_updated = []
        with transaction.atomic():
            for item in validated_data:
                email = item.pop("investor_email")
                inv = Investor.objects.get(email=email)
                obj, _ = Portfolio.objects.update_or_create(
                    investor=inv, name=item["name"], defaults={}
                )
                created_or_updated.append(obj)
        return created_or_updated


# bind list serializer
PortfolioUpsertSerializer.Meta.list_serializer_class = PortfolioUpsertListSerializer
