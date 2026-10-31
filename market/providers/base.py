import requests
from decimal import Decimal

class ExchangeAPIError(Exception):
    """Nothing just for raising ERROR's """

class BaseHttpClient:
    base_url = ''
    timeout = 5

    def _get(self, path, params=None, headers=None, data=None):
        try:
            response = requests.get(self.base_url + path, params=params, timeout=self.timeout, headers=headers, data=data)
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError) as exc:
            raise ExchangeAPIError(f'{self.__class__.__name__}: request failed: {path}') from exc

class PriceProvider:
    name = 'base'
    timeout = 5

    def fetch(self) -> Decimal:
        raise NotImplementedError