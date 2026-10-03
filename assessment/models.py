from django.db import models
from django.conf import settings


class Questions(models.Model):
    class Slot(models.TextChoices):
        INVESTMENT_GOAL = 'INVESTMENT_GOAL'
        TIME_HORIZON = 'TIME_HORIZON'
        LIQUIDITY = 'LIQUIDITY'
        EXTERNAL_RESOURCE = 'EXTERNAL_RESOURCE'
        IMPACT_OF_LOSS = 'IMPACT_OF_LOSS'
        RISK_TOLERANCE = 'RISK_TOLERANCE'
        RISK_PREFERENCE = 'RISK_PREFERENCE'
        RISK_PERCEPTION = 'RISK_PERCEPTION'
        KNOWLEDGE_1 = 'KNOWLEDGE_1'
        KNOWLEDGE_2 = 'KNOWLEDGE_2'
        KNOWLEDGE_3 = 'KNOWLEDGE_3'
        INVESTING_EXPERIENCE = 'INVESTING_EXPERIENCE'
        LOSS_EXPERIENCE = 'LOSS_EXPERIENCE'
        COMPOSURE_ACTUAL = 'COMPOSURE_ACTUAL'
        PAST_RISK_AWARENESS = 'PAST_RISK_AWARENESS'
        COMPOSURE_HYPOTHETICAL = 'COMPOSURE_HYPOTHETICAL'
        CONFLICT_FOLLOWUP = 'CONFLICT_FOLLOWUP'

    slot = models.CharField(choices=Slot.choices, max_length=30)
    text = models.CharField(max_length=200)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    version = models.PositiveIntegerField(default=1)
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
        unique_together = [('slot','version')]

class Choice(models.Model):
    question = models.ForeignKey(Questions, on_delete=models.CASCADE, related_name='choices')
    text = models.CharField(max_length=200)
    value = models.FloatField(null=True, blank=True)
    outcome = models.CharField(max_length=200,blank=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    update_at = models.DateTimeField(auto_now=True)
    deleted = models.BooleanField(default=False)

    def __str__(self):
        return self.text

    class Meta:
        db_table = 'choices'
        ordering = ['order']



class UserAnswers(models.Model):
    assessment = models.ForeignKey(RiskAssessment, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(Questions, on_delete=models.CASCADE)
    choice = models.ForeignKey(Choice, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted = models.BooleanField(default=False)

    class Meta:
        db_table = 'user_answers'


class RiskAssessment(models.Model):
    class Status(models.TextChoices):
        IN_PROGRESS = 'IN_PROGRESS'
        AWAITING_CONFLICT_RESOLUTION = 'AWAITING_CONFLICT_RESOLUTION'
        COMPLETED = 'COMPLETED'
        INCOMPLETE = 'INCOMPLETE'

    class Level(models.TextChoices):
        LOW = 'LOW'
        MEDIUM = 'MEDIUM'
        HIGH = 'HIGH'

    class ComposureSource(models.TextChoices):
        OBSERVED_PAST = 'OBSERVED_PAST'
        HYPOTHETICAL = 'HYPOTHETICAL'

    class Confidence(models.TextChoices):
        LOW = 'LOW'
        MEDIUM = 'MEDIUM'
        HIGH = 'HIGH'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='risk_assessments')
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.IN_PROGRESS)
    investment_goal = models.CharField(max_length=10, blank=True)
    investment_amount = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=10, default='USDT')
    time_horizon_score = models.FloatField(null=True, blank=True)
    liquidity_score = models.FloatField(null=True, blank=True)
    external_resources_score = models.FloatField(null=True, blank=True)
    impact_of_loss_score = models.FloatField(null=True, blank=True)
    risk_tolerance_score = models.FloatField(null=True, blank=True)
    risk_preference_score = models.FloatField(null=True, blank=True)
    risk_perception_raw_score = models.FloatField(null=True, blank=True)
    risk_perception_score = models.FloatField(null=True, blank=True)
    knowledge_correct_answers = models.PositiveIntegerField(null=True, blank=True)
    financial_knowledge_score = models.FloatField(null=True, blank=True)
    investing_experience_score = models.FloatField(null=True, blank=True)
    has_loss_experience = models.BooleanField(null=True, blank=True)
    risk_composure_score = models.FloatField(null=True, blank=True)
    composure_source = models.CharField(max_length=20, choices=ComposureSource.choices, null=True, blank=True)
    past_behavior_confidence = models.CharField(max_length=10, choices=Confidence.choices, null=True, blank=True)
    severe_behavioral_conflict = models.BooleanField(default=False)
    reverse_behavioral_conflict = models.BooleanField(default=False)
    conflict_answer = models.CharField(max_length=5, blank=True)
    conflict_resolved = models.BooleanField(null=True, blank=True)
    risk_ability_level = models.CharField(max_length=10, choices=Level.choices, null=True, blank=True)
    behavioral_score = models.FloatField(null=True, blank=True)
    behavioral_level = models.CharField(max_length=10, choices=Level.choices, null=True, blank=True)
    assessment_confidence = models.CharField(max_length=10, choices=Confidence.choices, null=True, blank=True)
    base_suitable_risk = models.CharField(max_length=10, choices=Level.choices, null=True, blank=True)
    suitable_risk_level = models.CharField(max_length=10, choices=Level.choices, null=True, blank=True)
    reason_codes = models.JSONField(default=list, blank=True)
    questionnaire_version = models.PositiveIntegerField(default=1)
    scoring_version = models.CharField(max_length=20, default='1.0')
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['started_at']
