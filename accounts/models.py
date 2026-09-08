import datetime
from django.contrib.auth.models import AbstractUser
from django.db import models
from core.models import Packages, RiskGroups


class User(AbstractUser):
    email = models.EmailField(unique=True)
    accessibility = models.IntegerField(default=0)
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        db_table = 'users'
        verbose_name = 'users'

class UserInformation(models.Model):
    name = models.CharField(max_length=100)
    surname = models.CharField(max_length=100)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    current_assets = models.JSONField(default=dict)
    risk_group = models.ForeignKey(RiskGroups, on_delete=models.CASCADE, null=True, blank=True)
    risk_score = models.IntegerField(default=1)
    joining_date = models.DateField(default=datetime.date.today)
    subscription_end_date = models.DateField(null=True, blank=True)
    package_assigned = models.ForeignKey(Packages, on_delete=models.CASCADE,
                                         null=True, blank=True)
    created_at = models.DateField(default=datetime.date.today)
    updated_at = models.DateField(auto_now=True)
    deleted = models.BooleanField(default=False)

    def __str__(self):
        return self.name
    class Meta:
        db_table = 'user_information'
        verbose_name = 'user_information'


