from decimal import Decimal
from .base import BaseHttpClient, ExchangeAPIError, PriceProvider


class NobitexClient(BaseHttpClient, PriceProvider):
    base_url = 'https://apiv2.nobitex.ir/'

    def __init__(self, symbol='USDTIRT'):
        self.symbol = symbol
        self.name = f'wallex_{symbol.lower()}'

    def get_last_trade_price(self, symbol):
        payload = {}
        headers = {
            'Accept': 'application/json'
        }
        try:
            data = self._get(f'/v2/trades/{symbol}', headers= headers, data=payload).json()
            return data['trades'][0]['price']

        except (KeyError, IndexError, TypeError) as exc:
            raise ExchangeAPIError('WallexClient: unexpected response shape') from exc

    def fetch(self):
        return Decimal(str(self.get_last_trade_price(self.symbol)))
