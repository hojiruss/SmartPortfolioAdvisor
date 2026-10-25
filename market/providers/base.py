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


class HttpPriceProvider(PriceProvider):
    url = 'TODO'
    headers = {}
    rial_to_toman = False  # بعضی منبع‌ها ریال می‌دهند؛ True کنید تا بر ۱۰ تقسیم شود

    def extract(self, data):
        """از پاسخ JSON فقط عدد قیمت را برگردان."""
        raise NotImplementedError

    def fetch(self):
        response = requests.get(self.url, headers=self.headers, timeout=self.timeout)
        response.raise_for_status()
        price = Decimal(str(self.extract(response.json())))
        return price / 10 if self.rial_to_toman else price