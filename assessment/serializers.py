from rest_framework import serializers
from .models import Questions, Choice, RiskAssessment, UserAnswers
from decimal import Decimal
from . import rules_config as rules


class ChoiceSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.question.slot == 'LOSS_EXPERIENCE':
            data['outcome'] = instance.outcome
        return data
    class Meta:
        model = Choice
        fields = ['id', 'text']

class QuestionSerializer(serializers.ModelSerializer):
    choices = ChoiceSerializer(many=True, read_only=True)
    class Meta:
        model = Questions
        fields = ['id', 'slot','text','choices']

class AnswerItemSerializer(serializers.ModelSerializer):
    question = serializers.PrimaryKeyRelatedField(queryset=Questions.objects.filter(is_active=True, deleted=False))
    choice = serializers.PrimaryKeyRelatedField(queryset=Choice.objects.filter(deleted=False))

    def validate_data(self, data):
        if data['choices'].question_id != data['questions'].id:
            raise serializers.ValidationError('این گزینه مربوط به این سوال نیست !!')
        return data

class SubmitAssessmentSerializer(serializers.ModelSerializer):
    investment_amount = serializers.IntegerField()
    answers = AnswerItemSerializer(many=True, allow_empty=False)

    def validate_answers(self, attrs):
        by_slot = {}
        questions = []

        for item in attrs['answers']:
            question = item['question']
            if question.slot in by_slot:
                raise serializers.ValidationError({'answers': ['برای هر سوال فقط یک پاسخ ارسال کنید']})
            by_slot[question.slot] = item['choice']
            questions.append(question)
        if rules.CONFLICT_SLOT in by_slot:
            raise serializers.ValidationError(
                {'answers': ['سوال تکمیلی تعارض از مسیر جداگانه پاسخ داده می‌شود']}
            )
        missing = [slot for slot in rules.ALWAYS_REQUIRED_SLOTS if slot not in by_slot]
        if missing:
            raise serializers.ValidationError(
                {'answers': ['لطفاً به تمام سوال‌های اصلی پاسخ دهید'], 'missing_slots': missing}
            )

        has_loss = by_slot['LOSS_EXPERIENCE'].outcome == rules.OUTCOME_HAS_LOSS
        required = rules.OBSERVED_PAST_SLOTS if has_loss else rules.HYPOTHETICAL_SLOTS
        forbidden = rules.HYPOTHETICAL_SLOTS if has_loss else rules.OBSERVED_PAST_SLOTS

        missing_branch = [slot for slot in required if slot not in by_slot]
        if missing_branch:
            raise serializers.ValidationError(
                {'answers': ['لطفاً به سوال‌های مربوط به تجربه‌ی سرمایه‌گذاری پاسخ دهید'],
                 'missing_slots': missing_branch}
            )

        if any(slot in by_slot for slot in forbidden):
            raise serializers.ValidationError(
                {'answers': ['پاسخ سوال‌های مربوط به مسیر دیگر نباید ارسال شود']}
            )

        versions = {question.version for question in questions}
        if len(versions) != 1:
            raise serializers.ValidationError({'answers': ['پاسخ‌ها باید مربوط به یک نسخه از پرسش‌نامه باشند']})

        attrs['choices_by_slot'] = by_slot
        attrs['questionnaire_version'] = versions.pop()
        return attrs

class ResolveConflictSerializer(serializers.Serializer):
    choice = serializers.PrimaryKeyRelatedField(
        queryset=Choice.objects.filter(
            deleted=False,
            question__slot=rules.CONFLICT_SLOT,
            question__is_active=True,
            question__deleted=False,
        )
    )

    def validate_choice(self, value):
        if value.outcome not in rules.VALID_CONFLICT_OUTCOMES:
            raise serializers.ValidationError('گزینه‌ی نامعتبر')
        return value

class AssessmentResultSerializer(serializers.ModelSerializer):
    assessment_id = serializers.IntegerField(source='id', read_only=True)
    summary = serializers.SerializerMethodField()

    class Meta:
        model = RiskAssessment
        fields = [
            'assessment_id', 'status', 'suitable_risk_level', 'summary',
            'reason_codes', 'completed_at', 'questionnaire_version', 'scoring_version',
        ]

    def get_summary(self, obj):
        return rules.RESULT_SUMMARIES.get(obj.suitable_risk_level)

