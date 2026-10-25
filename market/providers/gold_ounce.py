import requests as r
import os
from dotenv import load_dotenv
load_dotenv()
from .base import BaseHttpClient, PriceProvider, ExchangeAPIError



class GoldOunce(BaseHttpClient, PriceProvider):

    def get_ounce_gold_price(self):
        try:
            headers = {
                'x-access-token' : os.getenv('GOLD_API_KEY')
            }
            response = r.get(url='https://www.goldapi.io/api/price/XAU/USD', headers= headers).json()
            return int(response['price'])
        except (KeyError, IndexError, TypeError) as exc:
            raise ExchangeAPIError('WallexClient: unexpected response shape') from exc





