from datetime import datetime

from django.conf import settings
from django.utils import timezone
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .redis_interface import PriceStoreUnavailable, get_store


class PricesView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        try:
            raw_prices = get_store().get_all_prices()
        except PriceStoreUnavailable:
            return Response({'error': 'قیمت‌ها موقتاً در دسترس نیستند'}, status=503)

        now = timezone.now()
        prices = {}
        for symbol, item in raw_prices.items():
            if item is None:
                prices[symbol] = None
                continue
            age = (now - datetime.fromisoformat(item['updated_at'])).total_seconds()
            prices[symbol] = {**item, 'stale': age > settings.MARKET_STALE_AFTER_SECONDS}

        return Response({'prices': prices})