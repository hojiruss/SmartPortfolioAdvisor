from django.urls import path
from .views import (
    QuestionListView,
    SubmitAssessmentView,
    ResolveConflictView,
    AssessmentResultView,
    AssessmentHistoryView,
)

urlpatterns = [
    path('questions/', QuestionListView.as_view(), name='assessment_questions'),
    path('submit/', SubmitAssessmentView.as_view(), name='assessment_submit'),
    path('<int:assessment_id>/resolve-conflict/', ResolveConflictView.as_view(),
         name='assessment-resolve-conflict'),
    path('result/', AssessmentResultView.as_view(), name='assessment_result'),
    path('history/', AssessmentHistoryView.as_view(), name='assessment_history'),
]