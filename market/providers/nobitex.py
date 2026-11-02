from decimal import Decimal
from .base import BaseHttpClient, ExchangeAPIError, PriceProvider


class NobitexClient(BaseHttpClient, PriceProvider):
    base_url = 'https://apiv2.nobitex.ir'

    def __init__(self, symbol='USDTIRT'):
        self.symbol = symbol
        self.name = f'nobitex_{symbol.lower()}'


    def fetch(self):
        data = self._get(f'/v2/trades/{self.symbol}', headers={'Accept': 'application/json'})
        try:
            return Decimal(str(data['trades'][0]['price'])) / 10  # ریال به تومان
        except (KeyError, IndexError, TypeError) as exc:
            raise ExchangeAPIError('NobitexClient: unexpected response shape') from exc
