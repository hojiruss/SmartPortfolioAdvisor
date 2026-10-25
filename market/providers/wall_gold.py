import requests as r
from .base import BaseHttpClient, PriceProvider, ExchangeAPIError



class WallGoldClient(BaseHttpClient, PriceProvider):

    def get_gram_gold_price(self):
        try:
            response = r.get(url='https://api.wallgold.ir/api/v1/markets').json()
            gold_gram_tmn_price = 0
            for item, value in response.items():
                if value[0]['symbol'] == 'GLD_18C_750TMN':
                    gold_gram_tmn_price = value[0]['marketCap']['lastPrice']
                break
            return gold_gram_tmn_price
        except (KeyError, IndexError, TypeError) as exc:
            raise ExchangeAPIError('WallexClient: unexpected response shape') from exc






