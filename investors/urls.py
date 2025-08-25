from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AssetAnalyticsView,
    AssetViewSet,
    CachedAssetListView,
    InvestorProfileViewSet,
    InvestorViewSet,
    PortfolioViewSet,
)

router = DefaultRouter()
router.register("investors", InvestorViewSet)
router.register("profiles", InvestorProfileViewSet)
router.register("assets", AssetViewSet)
router.register(r"portfolios", PortfolioViewSet, basename="portfolio")

urlpatterns = [
    path("assets/analytics/", AssetAnalyticsView.as_view(), name="asset-analytics"),
    path("assets/cached/", CachedAssetListView.as_view(), name="asset-cached-list"),
    path("", include(router.urls)),
]
