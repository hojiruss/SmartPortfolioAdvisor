from django.db import models



class Packages(models.Model):
    package_name = models.CharField(max_length=100,unique=True)
    package_description = models.TextField(default="")
    package_price = models.DecimalField(max_digits=14, decimal_places=0, default=0)
    package_usage = models.IntegerField(default=0) # how many users have this package right now!
    deleted = models.BooleanField(default=False)
    class Meta:
        db_table = 'packages'
        verbose_name = 'packages'
        verbose_name_plural = 'packages'

class RiskGroups(models.Model):
    class RiskFactors(models.TextChoices):
        LOW_RISK = 'LOW_RISK'
        MODERATE = 'MODERATE'
        HIGH_RISK = 'HIGH_RISK'
    risk_group_name = models.CharField(max_length=100,unique=True)
    risk_group_description = models.TextField(default="")
    risk_factor = models.CharField(choices=RiskFactors.choices,max_length=20)
    deleted = models.BooleanField(default=False)
    class Meta:
        db_table = 'risk_groups'
        verbose_name = 'risk_groups'
        verbose_name_plural = 'risk_groups'

class AcceptedAssetGroup(models.Model):
    asset_group_name = models.CharField(max_length=100,unique=True)
    asset_group_description = models.TextField(default="")
    asset_group_member_count = models.IntegerField(default=0)
    risk_factor = models.ForeignKey(RiskGroups, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted = models.BooleanField(default=False)
    class Meta:
        db_table = 'asset_groups'
        verbose_name = 'asset_groups'

class AcceptedAssets(models.Model):
    asset_name = models.CharField(max_length=100,unique=True)
    asset_group = models.ForeignKey(AcceptedAssetGroup, on_delete=models.CASCADE)
    asset_description = models.TextField(default="")
    risk_score = models.IntegerField(default=0)
    risk_group = models.ForeignKey(RiskGroups, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted = models.BooleanField(default=False)
    class Meta:
        db_table = 'accepted_assets'
        verbose_name = 'accepted_assets'
        verbose_name_plural = 'accepted_assets'




