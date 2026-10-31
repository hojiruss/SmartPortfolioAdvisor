from decimal import Decimal
from .base import BaseHttpClient, PriceProvider, ExchangeAPIError



class WallGoldClient(BaseHttpClient, PriceProvider):
    base_url = 'https://api.wallgold.ir'
    name = 'wallgold_gold_gram'

    def fetch(self):
        data = self._get('/api/v1/markets')
        try:
            for markets in data.values():
                for item in markets:
                    if item['symbol'] == 'GLD_18C_750TMN':
                        return Decimal(str(item['marketCap']['lastPrice']))
        except (KeyError, IndexError, TypeError, AttributeError) as exc:
            raise ExchangeAPIError('WallGoldClient: unexpected response shape') from exc
        raise ExchangeAPIError('WallGoldClient: symbol not found')






