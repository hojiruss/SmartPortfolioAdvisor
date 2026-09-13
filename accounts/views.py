from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from . import services
from .serializers import VerifyOTPSerializer as VOS, RequestOTPSerializer as ROS
from .models import UserInformation


User = get_user_model()

class RequestOTPView(APIView):
    def post(self, request):
        serializer = ROS(data = request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']

        if not services.can_resend(email):
            return Response(
                {'error': 'لطفاً کمی صبر کنید و دوباره تلاش کنید'},
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )
        if services.resend_limit_reached(email):
            return Response(
                {'error': 'تعداد درخواست‌های شما در این ساعت بیش از حد مجاز است'},
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )
        services.generate_and_send_otp(email)
        return Response({'message':'کد ورود ارسال شد'}, status=status.HTTP_200_OK)

class VerifyOTPView(APIView):
    def post(self, request):
        serializer = VOS(data = request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        code = serializer.validated_data['code']

        result = services.verify_otp(email, code)

        if result=='expired':
            return Response({'error': 'کد منقضی شده است', 'state': 'expired'},
                            status=status.HTTP_400_BAD_REQUEST)

        if result=='wrong':
            return Response({'error': 'کد وارد شده اشتباه است', 'state': 'wrong'},
                            status=status.HTTP_400_BAD_REQUEST)

        if result=='max_attempts':
            return Response(
                {'error': 'تعداد تلاش‌های مجاز تمام شد', 'state': 'max_attempts'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'username':email,
            })
        if created:
            UserInformation.objects.create(user=user)

        refresh = RefreshToken.for_user(user)

        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'is_new_user': created,
        }, status=status.HTTP_200_OK)

class LogoutView(APIView):
    def post(self,request):
        try:
            refresh_token = request.data['refresh']
            token = RefreshToken(refresh_token) # type: ignore[call-arg]
            token.blacklist()
        except Exception:
            return Response({'error': 'توکن نامعتبر است'},
                            status=status.HTTP_400_BAD_REQUEST)

        return Response({'message': 'خروج موفق'}, status=status.HTTP_200_OK)

