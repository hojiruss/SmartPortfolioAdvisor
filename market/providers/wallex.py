from decimal import Decimal
from .base import BaseHttpClient, ExchangeAPIError, PriceProvider


class WallexClient(BaseHttpClient, PriceProvider):
    base_url = 'https://api.wallex.ir/'

    def __init__(self, symbol='USDTTMN'):
        self.symbol = symbol
        self.name = f'wallex_{symbol.lower()}'

    def get_last_trade_price(self, symbol):
        data = self._get('v1/trades', params={'symbol': symbol})
        try:
            if not data['success']:
                raise ExchangeAPIError('WallexClient: success=false')
            return data['result']['latestTrades'][0]['price']
        except (KeyError, IndexError, TypeError) as exc:
            raise ExchangeAPIError('WallexClient: unexpected response shape') from exc

    def fetch(self):
        return Decimal(str(self.get_last_trade_price(self.symbol)))