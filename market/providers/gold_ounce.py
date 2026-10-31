from decimal import Decimal
import os
from .base import BaseHttpClient, PriceProvider, ExchangeAPIError



class GoldOunce(BaseHttpClient, PriceProvider):
    base_url = 'https://www.goldapi.io'
    name = 'goldapi_xau_usd'

    def fetch(self):
        data = self._get(
            '/api/price/XAU/USD',
            headers={'x-access-token': os.getenv('GOLD_API_KEY', '')},
        )
        try:
            return Decimal(str(data['price']))
        except (KeyError, TypeError) as exc:
            raise ExchangeAPIError('GoldOunce: unexpected response shape') from exc





