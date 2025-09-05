from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from .health import health_view, ready_view

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("investors.urls")),
    path("health/", health_view, name="health"),
    path("ready/", ready_view, name="ready"),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
]
