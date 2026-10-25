import logging
from concurrent.futures import ThreadPoolExecutor
from statistics import median
from .providers import SYMBOL_CONFIG as sc
from .redis_interface import get_store
from .symbols import ALL_SYMBOLS


logger = logging.getLogger(__name__)

def aggregate(prices):
    return median(prices)

def safe_fetch(provider):
    try:
        price = provider.fetch()
        if not price.is_finite() or price <=0:
            raise ValueError(f'invalid price {price}')
        return price

    except Exception:
        logger.exception('price provider failed: %s', provider.name)
        return None

def collect_prices(providers):
    with ThreadPoolExecutor(max_workers=len(providers)) as pool:
        results = list(pool.map(safe_fetch, providers))
    return [price for price in results if price is not None]

def update_symbol(symbol, store):
    config = sc[symbol]
    prices = collect_prices(config['providers'])

    if len(prices) < config['min_sources']:
        logger.warning('not enough sources for %s: %s/%s', symbol, len(prices), config['min_sources'])
        return False

    store.set_prices(symbol, aggregate(prices), sources_used=len(prices))
    return True

def update_all_prices(store=None):
    store = store or get_store()
    return {symbol: update_symbol(symbol, store) for symbol in ALL_SYMBOLS}