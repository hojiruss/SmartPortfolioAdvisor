from django.urls import path
from .views import QuestionListView as QLV, SubmitAssessmentView as SAV, AssessmentResultView as ARV, QuestionListView, \
    SubmitAssessmentView, AssessmentResultView

urlpatterns = [
    path('questions/', QuestionListView.as_view(), name='assessment_questions'),
    path('submit/', SubmitAssessmentView.as_view(), name='assessment_submit'),
    path('result/', AssessmentResultView.as_view(), name='assessment_result'),
]