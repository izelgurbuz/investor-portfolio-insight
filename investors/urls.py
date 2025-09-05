from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AssetAnalyticsView,
    AssetViewSet,
    CachedAssetListView,
    InvestorProfileViewSet,
    InvestorViewSet,
    PortfolioBulkUpsertView,
    PortfolioViewSet,
)

router = DefaultRouter()
router.register("investors", InvestorViewSet)
router.register("profiles", InvestorProfileViewSet)
router.register("assets", AssetViewSet)
router.register("portfolios", PortfolioViewSet, basename="portfolio")

urlpatterns = [
    path(
        "portfolios/bulk-upsert/",
        PortfolioBulkUpsertView.as_view(),
        name="portfolio-bulk-upsert",
    ),
    path("assets/analytics/", AssetAnalyticsView.as_view(), name="asset-analytics"),
    path("assets/cached/", CachedAssetListView.as_view(), name="asset-cached-list"),
    path("", include(router.urls)),
]
