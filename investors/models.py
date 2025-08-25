from django.db import models


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
