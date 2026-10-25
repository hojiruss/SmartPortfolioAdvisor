import json
import redis
from datetime import datetime, timezone
from django.conf import settings
from .symbols import ALL_SYMBOLS

KEY_PREFIX = 'market:price:'

class PriceStoreUnavailable(Exception):
    """Raised when a price is not available/or something wrong with setting price in Redis"""

class RedisInterface:

    def __init__(self, client, ttl):
        self.client = client
        self.ttl = ttl

    def set_price(self, symbol, price, source_used):
        payload = {
            'price' : format(price, 'f'),
            'updated_at' : datetime.now(tz=timezone.utc).isoformat(),
            'source_used' : source_used,
        }
        try:
            self.client.set(KEY_PREFIX + symbol, json.dumps(payload), ex=self.ttl)
        except redis.RedisError as exc:
            raise PriceStoreUnavailable(str(exc)) from exc

    def get_all_price(self, symbols=ALL_SYMBOLS):
        try:
            raw_values = self.client.mget([KEY_PREFIX + symbol for symbol in symbols])
        except redis.RedisError as exc:
            raise PriceStoreUnavailable(str(exc)) from exc
        return {symbol: json.loads(raw) if raw else None for symbol, raw in zip(symbols, raw_values)}

    def get_price(self,symbol):
        return self.get_all_price([symbol])[symbol]


_store = None


def get_store():
    global _store
    if _store is None:
        client = redis.Redis.from_url(
            settings.MARKET_REDIS_URL,
            decode_responses=True,
            socket_timeout=2,
            socket_connect_timeout=2,
        )
        _store = RedisInterface(client, settings.MARKET_PRICE_TTL_SECONDS)
    return _store

