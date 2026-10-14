import logging
from django.db import transaction
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from . import rules_config as rules
from . import services
from .models import Questions, Choice, RiskAssessment, UserAnswers
from .serializers import (QuestionSerializer,
                          SubmitAssessmentSerializer,
                          ResolveConflictSerializer,
                          AssessmentResultSerializer,)

logger = logging.getLogger(__name__)

CALCULATION_ERRORS = (ValueError, KeyError, TypeError)
CALCULATION_FAILED_MESSAGE = 'خطایی در محاسبه‌ی نتیجه رخ داد. لطفاً دوباره تلاش کنید.'

def active_questions():
    return Questions.objects.filter(is_active=True, deleted = False).prefetch_related(
        Prefetch('choices', queryset=Choice.objects.filter(deleted=False))
    )

class QuestionListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        questions = active_questions().exclude(slot = rules.CONFLICT_SLOT)
        return Response(QuestionSerializer(questions, many=True).data)

class SubmitAssessmentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = SubmitAssessmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        choice_by_slot = data['choices_by_slot']

        try:
            engine_input = services.build_engine_input(choice_by_slot)
            result = services.run_assessment(engine_input)
        except CALCULATION_ERRORS:
            logger.exception('Risk Assessment calculation failed')
            return Response({'error': CALCULATION_FAILED_MESSAGE},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        awaiting = result['status'] == RiskAssessment.Status.AWAITING_CONFLICT_RESOLUTION
        conflict_question = None
        if awaiting:
            conflict_question = active_questions().filter(slot = rules.CONFLICT_SLOT).first()
            if conflict_question is None:
                logger.error('Conflict follow-up question is missing from the questionnaire')
                return Response({'error': CALCULATION_FAILED_MESSAGE}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        fields = services.build_assessment_fields(engine_input, result)

        with transaction.atomic():
            RiskAssessment.objects.filter(
                user = request.user, status = RiskAssessment.Status.AWAITING_CONFLICT_RESOLUTION
            ).update(status = RiskAssessment.Status.INCOMPLETE)

            assessment = RiskAssessment(
                user = request.user,
                investment_amount=data['investment_amount'],
                currency=data['currency'],
                questionnaire_version=data['questionnaire_version'],
                **fields,
            )
            if not awaiting:
                assessment.completed_at = timezone.now()
            assessment.save()

            UserAnswers.objects.bulk_create([
                UserAnswers(assessment=assessment, question=item['question'], choice=item['choice'])
                for item in data['answers']
            ])

        if awaiting:
            return Response({
                'assessment_id': assessment.id,
                'status': assessment.status,
                'conflict_question': QuestionSerializer(conflict_question).data,
            })

        return Response(AssessmentResultSerializer(assessment).data)


class ResolveConflictView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, assessment_id):
        serializer = ResolveConflictSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        choice = serializer.validated_data['choice']

        with transaction.atomic():
            assessment = get_object_or_404(
                RiskAssessment.objects.select_for_update(), pk=assessment_id, user=request.user
            )

            if assessment.status != RiskAssessment.Status.AWAITING_CONFLICT_RESOLUTION:
                return Response(
                    {'error': 'این ارزیابی منتظر پاسخ سوال تکمیلی نیست'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                result = services.resolved_conflict_and_finalize(
                    assessment.risk_ability_level, assessment.behavioral_level, choice.outcome
                )
            except CALCULATION_ERRORS:
                logger.exception('Conflict resolution failed')
                return Response({'error': CALCULATION_FAILED_MESSAGE}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            assessment.conflict_answer = choice.outcome
            assessment.conflict_resolved = result['conflict_resolved']
            assessment.assessment_confidence = result['assessment_confidence']
            assessment.base_suitable_risk = result['base_suitable_risk']
            assessment.suitable_risk_level = result['suitable_risk_level']
            if result['unresolved_reason']:
                assessment.reason_codes = assessment.reason_codes + [result['unresolved_reason']]
            assessment.status = RiskAssessment.Status.COMPLETED
            assessment.completed_at = timezone.now()
            assessment.save()

            UserAnswers.objects.create(assessment=assessment, question=choice.question, choice=choice)

        return Response(AssessmentResultSerializer(assessment).data)


class AssessmentResultView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        assessment = (
            RiskAssessment.objects
            .filter(user=request.user, status=RiskAssessment.Status.COMPLETED)
            .order_by('-completed_at')
            .first()
        )
        if assessment is None:
            return Response({'error': 'هنوز ارزیابی ریسک انجام نداده‌اید'}, status=status.HTTP_404_NOT_FOUND)
        return Response(AssessmentResultSerializer(assessment).data)


class AssessmentHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        assessments = (
            RiskAssessment.objects
            .filter(user=request.user, status=RiskAssessment.Status.COMPLETED)
            .order_by('-completed_at')
        )
        return Response(AssessmentResultSerializer(assessments, many=True).data)
