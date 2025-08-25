import factory
from factory.django import DjangoModelFactory

from investors.models import Asset, Investor, InvestorProfile, Portfolio


class InvestorFactory(DjangoModelFactory):
    class Meta:
        model = Investor

    name = factory.Sequence(lambda n: f"user{n}")
    email = factory.Sequence(lambda n: f"user{n}@demo.com")


class InvestorProfileFactory(DjangoModelFactory):
    class Meta:
        model = InvestorProfile

    investor = factory.SubFactory(InvestorFactory)
    risk_tolerance = "medium"
    experience_level = "Intermediate"


class AssetFactory(DjangoModelFactory):
    class Meta:
        model = Asset

    name = factory.Sequence(lambda n: f"TICK{n}")
    category = "Equity"
    price = 100
    volatility = 0.2


class PortfolioFactory(DjangoModelFactory):
    class Meta:
        model = Portfolio


investor = factory.SubFactory(InvestorFactory)
name = factory.Sequence(lambda n: f"Portfolio {n}")


@factory.post_generation
def assets(self, create, extracted, **kwargs):
    if not create:
        return
    if extracted:
        self.assets.add(*extracted)
