from __future__ import annotations

from datetime import datetime, timezone
from email.utils import format_datetime

from django.db.models import (
    Avg,
    Case,
    CharField,
    Count,
    ExpressionWrapper,
    F,
    FloatField,
    IntegerField,
    Max,
    Prefetch,
    Q,
    Value,
    When,
)
from django.db.models.functions import Coalesce, Sqrt
from django.http import HttpResponseNotModified
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from investors.filters import PortfolioFilter
from investors.metrics_services import annotate_metrics
from investors.models import Asset, Portfolio
from investors.serializers import PortfolioUpsertSerializer

from .models import Investor, InvestorProfile
from .serializers import (
    AssetSerializer,
    InvestorProfileSerializer,
    InvestorSerializer,
    PortfolioDetailSerializer,
    PortfolioSummarySerializer,
)


class InvestorViewSet(viewsets.ModelViewSet):
    queryset = Investor.objects.all()
    serializer_class = InvestorSerializer


class InvestorProfileViewSet(viewsets.ModelViewSet):
    queryset = InvestorProfile.objects.all()
    serializer_class = InvestorProfileSerializer


class AssetViewSet(viewsets.ModelViewSet):
    queryset = Asset.objects.all()
    serializer_class = AssetSerializer


class PortfolioViewSet(viewsets.ModelViewSet):
    filterset_class = PortfolioFilter
    ordering_fields = ["name", "asset_count", "port_vol", "sharpe_proxy"]
    ordering = ["-sharpe_proxy"]

    def get_serializer_class(self):
        return (
            PortfolioDetailSerializer
            if self.action == "retrieve"
            else PortfolioSummarySerializer
        )

    def get_queryset(self):
        base = annotate_metrics(Portfolio.objects.all())

        if self.action == "retrieve":
            return base.select_related("investor").prefetch_related(
                Prefetch(
                    "assets",
                    queryset=Asset.objects.only("id", "name", "price", "volatility"),
                )
            )
        # list / others
        return base.select_related("investor")

    @action(detail=False, methods=["GET"])
    def top(self, request):
        limit = int(request.query_params.get("limit", 5))
        # respects ?risk=... & ?min_sharpe=... & ?ordering=...
        qs = self.filter_queryset(self.get_queryset()).order_by("-sharpe_proxy")[:limit]
        ser = PortfolioSummarySerializer(qs, many=True)
        return Response(ser.data)

    @action(detail=True, methods=["GET"])
    def stats(self, request, pk=None):
        obj = self.get_object()
        return Response(
            {
                "volatility": obj.port_vol,
                "sharpe": obj.sharpe_proxy,
            }
        )


class AssetAnalyticsView(APIView):
    """
    Analytics on assets:
      - Filters to "interesting" assets (EQUITY or high vol)
      - Summary stats
      - Count per risk band (low/medium/high by volatility)
      - Interpretable risk: average daily typical move in currency units
    """

    def get(self, request):
        base = Asset.objects.all()

        interesting = base.filter(Q(category="Equity") | Q(volatility__gt=0.30))

        # Risk band by annualized volatility thresholds (tune as needed)
        risk_band = Case(
            When(volatility__lt=0.15, then=Value("low")),
            When(volatility__lt=0.25, then=Value("medium")),
            default=Value("high"),
            output_field=CharField(),
        )

        summary = interesting.aggregate(
            n_total=Count("id", distinct=True),
            n_distinct_names=Count("name", distinct=True),
            avg_price=Coalesce(Avg("price"), Value(0.0)),
            max_vol=Coalesce(Max("volatility"), Value(0.0)),
        )

        per_band_qs = (
            interesting.annotate(risk_band=risk_band)
            .values("risk_band")
            .annotate(n=Count("id"))
        )

        # impose custom ordering by band label
        band_order = Case(
            When(risk_band="low", then=Value(1)),
            When(risk_band="medium", then=Value(2)),
            When(risk_band="high", then=Value(3)),
            default=Value(99),
            output_field=IntegerField(),
        )
        per_band = list(
            per_band_qs.annotate(order_key=band_order)
            .order_by("order_key")
            .values("risk_band", "n")
        )

        # Interpretable risk: typical daily move in currency units
        daily_sigma = ExpressionWrapper(
            F("volatility") / Sqrt(Value(252.0)),
            output_field=FloatField(),
        )
        daily_move = ExpressionWrapper(
            F("price") * daily_sigma,
            output_field=FloatField(),
        )
        daily_move_stats = interesting.annotate(daily_move=daily_move).aggregate(
            avg_daily_move=Coalesce(Avg("daily_move"), Value(0.0)),
            max_daily_move=Coalesce(Max("daily_move"), Value(0.0)),
        )

        return Response(
            {
                "summary": summary,
                "per_band": per_band,
                "interpretable_risk": {
                    "avg_daily_move": daily_move_stats["avg_daily_move"],
                    "max_daily_move": daily_move_stats["max_daily_move"],
                    "units": "same as price (per trading day)",
                },
            }
        )


class CachedAssetListView(APIView):
    """
    Weak ETag + Last-Modified for a minimal list swap to updated_at TO-DO
    """

    def get(self, request):
        qs = Asset.objects.only("id", "name").order_by("id")
        count = qs.count()
        last = qs.last()
        max_id = last.id if last else 0

        etag = f'W/"assets:{count}:{max_id}"'
        if request.headers.get("If-None-Match") == etag:
            resp = HttpResponseNotModified()
            resp["ETag"] = etag
            return resp

        dt = datetime.fromtimestamp(max(1, max_id), tz=timezone.utc)
        last_mod = format_datetime(dt)
        if request.headers.get("If-Modified-Since") == last_mod:
            resp = HttpResponseNotModified()
            resp["ETag"] = etag
            resp["Last-Modified"] = last_mod
            return resp

        data = list(qs.values("id", "name"))
        resp = Response(data)
        resp["ETag"] = etag
        resp["Last-Modified"] = last_mod
        return resp


class PortfolioBulkUpsertView(APIView):
    permission_classes = [permissions.IsAdminUser]  # adjust if needed

    def post(self, request):
        if not isinstance(request.data, list):
            return Response(
                {"detail": "Expected a JSON list"}, status=status.HTTP_400_BAD_REQUEST
            )
        ser = PortfolioUpsertSerializer(data=request.data, many=True)
        ser.is_valid(raise_exception=True)
        objs = ser.save()
        return Response(
            {"count": len(objs), "ids": [o.id for o in objs]}, status=status.HTTP_200_OK
        )
