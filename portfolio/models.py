from django.db import models


class PortfolioSet(models.Model):
    version = models.PositiveIntegerField(unique=True)
    is_active = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"v{self.version}"


class Portfolio(models.Model):
    class Profile(models.TextChoices):
        LOW = "LOW"
        MEDIUM = "MEDIUM"
        HIGH = "HIGH"

    portfolio_set = models.ForeignKey(PortfolioSet, on_delete=models.PROTECT, related_name="portfolios")
    code = models.CharField(max_length=2)
    profile = models.CharField(max_length=6, choices=Profile.choices)
    risk_score = models.PositiveSmallIntegerField()
    description = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["portfolio_set", "code"], name="uniq_portfolio_code_per_set"),
        ]


class PortfolioWeight(models.Model):
    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name="weights")
    asset = models.ForeignKey("core.AcceptedAssets", on_delete=models.PROTECT)
    weight = models.DecimalField(max_digits=5, decimal_places=2)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["portfolio", "asset"], name="uniq_weight_per_asset"),
        ]