from market.symbols import USDT_IRT, GOLD_GRAM_IRT, GOLD_OUNCE_USD
from .wall_gold import WallGoldClient
from .gold_ounce import GoldOunce
from .wallex import WallexClient
from .nobitex import NobitexClient

SYMBOL_CONFIG = {
    USDT_IRT: {'providers': [WallexClient(), NobitexClient()], 'min_sources': 1},
    GOLD_GRAM_IRT: {'providers': [WallGoldClient()], 'min_sources': 1},
    GOLD_OUNCE_USD: {'providers': [GoldOunce()], 'min_sources': 1},
}