from django.db import models
from django.conf import settings


class Questions(models.Model):
    text = models.CharField(max_length=200)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted = models.BooleanField(default=False)

    def __str__(self):
        return self.text

    class Meta:
        db_table = 'questions'
        ordering = ['order']
        verbose_name = 'Question'
        verbose_name_plural = 'Questions'

class Choice(models.Model):
    question = models.ForeignKey(Questions, on_delete=models.CASCADE, related_name='choices')
    text = models.CharField(max_length=200)
    score = models.PositiveIntegerField(default=0)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    update_at = models.DateTimeField(auto_now=True)
    deleted = models.BooleanField(default=False)

    def __str__(self):
        return self.text

    class Meta:
        db_table = 'choices'
        ordering = ['order']



class UserAssessment(models.Model):
    class RiskProfile(models.TextChoices):
        CONSERVATIVE = 'CONSERVATIVE'
        MODERATE = 'MODERATE'
        AGGRESSIVE = 'AGGRESSIVE'
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='Answers')
    score = models.PositiveIntegerField(default=0)
    risk_profile = models.CharField(choices=RiskProfile.choices, max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted = models.BooleanField(default=False)

    class Meta:
        db_table = 'user_assessment'



class UserAnswers(models.Model):
    assessment = models.ForeignKey(UserAssessment, on_delete=models.CASCADE)
    question = models.ForeignKey(Questions, on_delete=models.CASCADE)
    choice = models.ForeignKey(Choice, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted = models.BooleanField(default=False)

    class Meta:
        db_table = 'user_answers'

