import datetime

from django.db import models

from accounts.models import User
from core.models import Packages


class UserPayments(models.Model):
    class PaymentStatus(models.TextChoices):
        PROCESSING = 'PROCESSING'
        COMPLETED = 'COMPLETED'
        FAILED = 'FAILED'

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    package = models.ForeignKey(Packages, on_delete=models.CASCADE)
    status = models.CharField(
        choices=PaymentStatus.choices,
        max_length=20,
        default=PaymentStatus.PROCESSING,
    )
    created_at = models.DateField(default=datetime.date.today)
    updated_at = models.DateField(auto_now=True)
    deleted = models.BooleanField(default=False)

    class Meta:
        db_table = 'user_payments'
        verbose_name = 'user_payments'
        ordering = ['created_at']