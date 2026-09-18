from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from .models import Questions, Choice, UserAssessment, UserAnswers
from .serializers import QuestionSerializer as qs, SubmitAssessmentSerializer as sas

def classify_risk(score):
    if score <= 34:
        return UserAssessment.RiskProfile.CONSERVATIVE
    elif score <= 65:
        return UserAssessment.RiskProfile.MODERATE
    return UserAssessment.RiskProfile.AGGRESSIVE

class QuestionListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        questions = Questions.objects.filter(is_active=True).prefetch_related('choices')
        serializer = qs(questions, many=True)
        return Response(serializer.data)

class SubmitAssessmentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = sas(data=request.data)
        serializer.is_valid(raise_exception=True)
        answers = serializer.validated_data['answers']

        total_score = sum(item['choice'].score for item in answers)
        risk_profile = classify_risk(total_score)

        assessment , _= UserAssessment.objects.update_or_create(
            user=request.user,
            defaults={
                'score': total_score,
                'risk_profile': risk_profile,
            }
        )

        assessment.answers.all().delete()

        UserAnswers.objects.bulk_create([
            UserAnswers(assessment=assessment, question= item['question'], choice= item['choices'])
            for item in answers
        ])

        return Response({
            'score': assessment.score,
            'risk_profile': assessment.risk_profile,
        }, status=status.HTTP_200_OK)

class AssessmentResultView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            assessment = request.user.userassessment
        except UserAssessment.DoesNotExist:
            return Response(
                {'error':'هنوز ارزیابی ریسک انجام نداده اید'},
                status= status.HTTP_404_NOT_FOUND
            )

        return Response({
            'score': assessment.score,
            'risk_profile': assessment.risk_profile,
            'created_at': assessment.created_at,
        })





# Create your views here.
