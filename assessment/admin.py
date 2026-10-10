from django.contrib import admin
from .models import Questions, Choice, RiskAssessment, UserAnswers

class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 0

@admin.register(Questions)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['order', 'slot', 'text', 'version', 'is_active', 'delete']
    list_filter = ['version', 'is_active', 'deleted']
    inlines = [ChoiceInline]

class UserAnswersInline(admin.TabularInline):
    model = UserAnswers
    extra = 0
    can_delete = False
    readonly_fields = ['question', 'choice']

@admin.register(RiskAssessment)
class RiskAssessmentAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'status', 'risk_ability_level', 'behavioral_level',
                    'suitable_risk_level', 'assessment_confidence', 'completed_at']
    list_filter = ['status', 'suitable_risk_level']
    inlines = [UserAnswersInline]


