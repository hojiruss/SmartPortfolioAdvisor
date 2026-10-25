import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from io import StringIO
from unittest import mock

import redis
from django.conf import settings
from django.core.management import call_command
from django.test import SimpleTestCase
from rest_framework.test import APISimpleTestCase

from . import services
from .providers.base import PriceProvider
from .redis_interface import KEY_PREFIX, PriceStoreUnavailable, RedisInterface
from .symbols import ALL_SYMBOLS, GOLD_GRAM_IRT, GOLD_OUNCE_USD, USDT_IRT
from .tasks import update_prices_task


class FakeRedis:
    def __init__(self):
        self.data, self.ttls, self.down = {}, {}, False

    def set(self, key, value, ex=None):
        if self.down:
            raise redis.ConnectionError('down')
        self.data[key], self.ttls[key] = value, ex

    def mget(self, keys):
        if self.down:
            raise redis.ConnectionError('down')
        return [self.data.get(key) for key in keys]


class FakeProvider(PriceProvider):
    def __init__(self, value, name='fake'):
        self.value, self.name = value, name

    def fetch(self):
        if isinstance(self.value, Exception):
            raise self.value
        return Decimal(str(self.value))


def cfg(*values, min_sources=2):
    return {'providers': [FakeProvider(v, f'p{i}') for i, v in enumerate(values)], 'min_sources': min_sources}


def fill_config(**overrides):
    base = {symbol: cfg(1, min_sources=1) for symbol in ALL_SYMBOLS}
    base.update(overrides)
    return base


class AggregateTests(SimpleTestCase):
    def test_median(self):
        self.assertEqual(services.aggregate([Decimal(1), Decimal(100), Decimal(3)]), 3)
        self.assertEqual(services.aggregate([Decimal(10), Decimal(20)]), 15)


class UpdateTests(SimpleTestCase):
    def setUp(self):
        self.fake = FakeRedis()
        self.store = RedisInterface(self.fake, ttl=900)

    def run_update(self, symbol, config):
        with mock.patch.dict(services.SYMBOL_CONFIG, {symbol: config}):
            return services.update_symbol(symbol, self.store)

    def stored(self, symbol=USDT_IRT):
        return self.store.get_price(symbol)

    def test_all_sources_ok_stores_the_median(self):
        self.assertTrue(self.run_update(USDT_IRT, cfg(100, 102, 101)))
        item = self.stored()
        self.assertEqual(item['price'], '101')
        self.assertEqual(item['sources_used'], 3)
        self.assertEqual(self.fake.ttls[KEY_PREFIX + USDT_IRT], 900)

    def test_a_failing_source_is_skipped(self):
        with self.assertLogs('market.services', level='ERROR'):
            self.assertTrue(self.run_update(USDT_IRT, cfg(100, RuntimeError('boom'), 102)))
        self.assertEqual(self.stored()['sources_used'], 2)

    def test_not_enough_sources_keeps_the_previous_price(self):
        self.run_update(USDT_IRT, cfg(100, 100, 100))
        with self.assertLogs('market.services'):
            self.assertFalse(self.run_update(USDT_IRT, cfg(RuntimeError('a'), RuntimeError('b'), 105)))
        self.assertEqual(self.stored()['price'], '100')

    def test_invalid_prices_are_discarded(self):
        with self.assertLogs('market.services', level='ERROR'):
            ok = self.run_update(USDT_IRT, cfg(0, -5, 'NaN', 50, min_sources=1))
        self.assertTrue(ok)
        self.assertEqual(self.stored()['price'], '50')
        self.assertEqual(self.stored()['sources_used'], 1)

    def test_price_is_stored_without_scientific_notation(self):
        self.run_update(GOLD_GRAM_IRT, cfg('1E+5', min_sources=1))
        self.assertEqual(self.stored(GOLD_GRAM_IRT)['price'], '100000')

    def test_update_all_reports_each_symbol(self):
        config = fill_config(**{GOLD_OUNCE_USD: cfg(RuntimeError('x'), min_sources=1)})
        with mock.patch.dict(services.SYMBOL_CONFIG, config), self.assertLogs('market.services'):
            result = services.update_all_prices(self.store)
        self.assertEqual(result, {USDT_IRT: True, GOLD_GRAM_IRT: True, GOLD_OUNCE_USD: False})


class StoreTests(SimpleTestCase):
    def test_missing_symbols_are_none(self):
        store = RedisInterface(FakeRedis(), ttl=900)
        self.assertEqual(store.get_all_prices(), {symbol: None for symbol in ALL_SYMBOLS})

    def test_redis_errors_become_price_store_unavailable(self):
        fake = FakeRedis()
        fake.down = True
        store = RedisInterface(fake, ttl=900)
        with self.assertRaises(PriceStoreUnavailable):
            store.set_price(USDT_IRT, Decimal(1), 1)
        with self.assertRaises(PriceStoreUnavailable):
            store.get_all_prices()


class PricesViewTests(APISimpleTestCase):
    def setUp(self):
        self.fake = FakeRedis()
        self.store = RedisInterface(self.fake, ttl=900)
        patcher = mock.patch('market.views.get_store', return_value=self.store)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_returns_prices_and_nulls_for_missing(self):
        self.store.set_price(USDT_IRT, Decimal('98500.5'), 3)
        response = self.client.get('/api/market/prices/')
        self.assertEqual(response.status_code, 200)
        prices = response.json()['prices']
        self.assertEqual(prices[USDT_IRT]['price'], '98500.5')
        self.assertEqual(prices[USDT_IRT]['sources_used'], 3)
        self.assertFalse(prices[USDT_IRT]['stale'])
        self.assertIsNone(prices[GOLD_GRAM_IRT])

    def test_old_prices_are_marked_stale(self):
        old = datetime.now(timezone.utc) - timedelta(seconds=settings.MARKET_STALE_AFTER_SECONDS + 5)
        self.fake.data[KEY_PREFIX + USDT_IRT] = json.dumps(
            {'price': '1', 'updated_at': old.isoformat(), 'sources_used': 1}
        )
        self.assertTrue(self.client.get('/api/market/prices/').json()['prices'][USDT_IRT]['stale'])

    def test_redis_down_gives_503(self):
        self.fake.down = True
        self.assertEqual(self.client.get('/api/market/prices/').status_code, 503)

    def test_endpoint_is_public_even_with_a_bad_token(self):
        response = self.client.get('/api/market/prices/', HTTP_AUTHORIZATION='Bearer expired.or.invalid')
        self.assertEqual(response.status_code, 200)


class TaskAndCommandTests(SimpleTestCase):
    def test_task_runs_the_service(self):
        with mock.patch('market.tasks.update_all_prices', return_value={USDT_IRT: True}):
            self.assertEqual(update_prices_task(), {USDT_IRT: True})

    def test_beat_schedule_points_to_the_registered_task(self):
        entry = settings.CELERY_BEAT_SCHEDULE['update-market-prices']
        self.assertEqual(entry['task'], update_prices_task.name)
        self.assertEqual(entry['schedule'], 300.0)

    def test_management_command(self):
        out = StringIO()
        with mock.patch('market.management.commands.update_prices.update_all_prices',
                        return_value={USDT_IRT: True, GOLD_GRAM_IRT: False}):
            call_command('update_prices', stdout=out)
        self.assertIn('USDT_IRT: OK', out.getvalue())
        self.assertIn('GOLD_GRAM_IRT: FAILED', out.getvalue())