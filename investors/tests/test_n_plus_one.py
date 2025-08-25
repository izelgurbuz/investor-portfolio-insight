import pytest
from django.db.models import Prefetch
from django.urls import reverse
from rest_framework.test import APIClient

from investors.models import Asset, Portfolio
from investors.tests.factories import (
    AssetFactory,
    InvestorFactory,
    PortfolioFactory,
)


def load_portfolios_naive():
    return Portfolio.objects.all()


def load_portfolios_optimized():
    assets_qs = Asset.objects.only("id", "name", "price")
    return (
        Portfolio.objects.select_related("investor")
        .prefetch_related(Prefetch("assets", queryset=assets_qs))
        .only("id", "investor__name", "investor__id")
    )


@pytest.mark.django_db
def test_naive_triggers_n_plus_one(django_assert_max_num_queries):
    assets = AssetFactory.create_batch(8)

    for _ in range(10):
        p = PortfolioFactory(investor=InvestorFactory())
        p.assets.add(*assets)

    def iterate():
        for p in load_portfolios_naive():
            for p in load_portfolios_naive():
                _ = p.investor.name
                for a in p.assets.all():
                    _ = (a.name, a.price)

        with pytest.raises(AssertionError):
            # unrealistically low threshold to demonstrate failure for naive
            with django_assert_max_num_queries(5):
                iterate()


@pytest.mark.django_db
def test_optimized_limits_queries(django_assert_max_num_queries):
    assets = AssetFactory.create_batch(8)
    for _ in range(10):
        p = PortfolioFactory(investor=InvestorFactory())
        p.assets.add(*assets)

    # Optimized: should be ≈ 2–3 queries (1 main + 1 prefetch; select_related does not add)
    def iterate():
        for p in load_portfolios_optimized():
            _ = p.investor.name
            for a in p.assets.all():
                _ = (a.name, a.price)

    with django_assert_max_num_queries(3):
        iterate()


@pytest.mark.django_db
def test_portfolio_list_endpoint(django_assert_max_num_queries):
    assets = AssetFactory.create_batch(25)
    p = PortfolioFactory(investor=InvestorFactory())
    p.assets.set(assets)

    client = APIClient()
    url = reverse("portfolio-list")

    with django_assert_max_num_queries(3):
        res = client.get(url)

    assert res.status_code == 200
    body = res.json()
    body["count"] >= 1
    print(body["results"][0])
    assert body["results"][0]["asset_count"] == 25
