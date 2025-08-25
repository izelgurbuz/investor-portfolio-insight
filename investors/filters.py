import django_filters as filters

from investors.models import Portfolio


class PortfolioFilter(filters.FilterSet):
    risk = filters.CharFilter(method="filter_risk")
    min_sharpe = filters.NumberFilter(field_name="sharpe_proxy", lookup_expr="gte")

    def filter_risk(self, queryset, name, value):
        band = (value or "").strip().lower()
        if band == "low":
            return queryset.filter(port_vol__lt=0.15)
        elif band == "medium":
            return queryset.filter(port_vol__gte=0.15, port_vol__lt=0.25)
        elif band == "high":
            return queryset.filter(port_vol__gte=0.25)
        return queryset

    class Meta:
        model = Portfolio
        fields = ["risk", "min_sharpe"]
