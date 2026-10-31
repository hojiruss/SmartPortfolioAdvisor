from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from .models import AboutItem,FAQItem
class HomeView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        return Response({
            'title': 'Home Page',
            'description': 'This is the home page',
        })

class AboutView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        about = AboutItem.objects.filter(deleted=False).first()
        return Response({
            'description': about.description if about else ''
        })

class FAQView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        items = FAQItem.objects.filter(deleted=False)
        data = [{'question': i.question, 'answer': i.answer} for i in items]
        return Response({
            'items': data
        })