from rest_framework import serializers
from .models import Questions, Choice, UserAssessment, UserAnswers


class ChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        fields = ['id', 'text']

class QuestionSerializer(serializers.ModelSerializer):
    choices = ChoiceSerializer(many=True, read_only=True)
    class Meta:
        model = Questions
        fields = ['id', 'text','choices']

class AnswerItemSerializer(serializers.ModelSerializer):
    questions = serializers.PrimaryKeyRelatedField(queryset=Questions.objects.filter(is_active=True))
    choices = serializers.PrimaryKeyRelatedField(queryset=Choice.objects.all())

    def validate_data(self, data):
        if data['choices'].question_id != data['questions'].id:
            raise serializers.ValidationError('این گزینه مربوط به این سوال نیست !!')
        return data

class SubmitAssessmentSerializer(serializers.ModelSerializer):
    answers = AnswerItemSerializer(many=True)

    def validate_answers(self, value):
        active_ids = set(Questions.objects.filter(is_active=True).values_list('id', flat=True))
        submitted_ids = set([item['question'].id for item in value])

        if submitted_ids != active_ids:
            raise serializers.ValidationError('لطفا به تمامی سوالات پاسخ دهید !!')
        return value

