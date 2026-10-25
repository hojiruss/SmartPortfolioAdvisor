from django.urls import path
from .views import PricesView

urlpatterns = [
    path('prices/', PricesView.as_view(), name='market_prices'),
]