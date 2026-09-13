from django.urls import path
from .views import RequestOTPView as ROV, VerifyOTPView as VOV, LogoutView as LV
from rest_framework_simplejwt.views import TokenRefreshView


urlpatterns = [
    path('request-otp/', ROV.as_view(), name='request-otp'),
    path('verify-otp/', VOV.as_view(), name='verify-otp'),
    path('logout/', LV.as_view(), name='logout'),
    path('token-refresh/', TokenRefreshView.as_view(), name='token-refresh')
]