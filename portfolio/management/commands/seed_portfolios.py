from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from core.models import AcceptedAssetGroup, AcceptedAssets, RiskGroups
from portfolio.models import Portfolio, PortfolioSet, PortfolioWeight

F = RiskGroups.RiskFactors

ASSETS = {
    'YAGHOUT': ('یاقوت آگاه', 'درآمد ثابت', F.LOW_RISK),
    'AYAR': ('عیار مفید', 'طلا', F.MODERATE),
    'ARAM': ('آرام مفید', 'سهام', F.HIGH_RISK),
    'BTC': ('بیت‌کوین', 'دارایی دیجیتال', F.HIGH_RISK),
}

SEED = {
    'C1': ('LOW', 7, {'YAGHOUT': 80, 'AYAR': 15, 'ARAM': 5}),
    'C2': ('LOW', 20, {'YAGHOUT': 70, 'AYAR': 20, 'ARAM': 10}),
    'C3': ('LOW', 31, {'YAGHOUT': 60, 'AYAR': 20, 'ARAM': 20}),
    'M1': ('MEDIUM', 41, {'YAGHOUT': 45, 'AYAR': 25, 'ARAM': 30}),
    'M2': ('MEDIUM', 52, {'YAGHOUT': 35, 'AYAR': 25, 'ARAM': 40}),
    'M3': ('MEDIUM', 62, {'YAGHOUT': 25, 'AYAR': 25, 'ARAM': 50}),
    'A1': ('HIGH', 71, {'AYAR': 28, 'ARAM': 70, 'BTC': 2}),
    'A2': ('HIGH', 81, {'AYAR': 25, 'ARAM': 71, 'BTC': 4}),
    'A3': ('HIGH', 93, {'AYAR': 22, 'ARAM': 72, 'BTC': 6}),
}


def get_asset(symbol, name, group_name, factor):
    risk_group, _ = RiskGroups.objects.get_or_create(
        risk_factor=factor, defaults={'risk_group_name': factor})
    group, _ = AcceptedAssetGroup.objects.get_or_create(
        asset_group_name=group_name, defaults={'risk_factor': risk_group})
    asset, _ = AcceptedAssets.objects.get_or_create(
        symbol=symbol, defaults={'asset_name': name, 'asset_group': group, 'risk_group': risk_group})
    return asset


class Command(BaseCommand):
    help = 'Seed portfolio set v1 (9 fixed portfolios)'

    @transaction.atomic
    def handle(self, *args, **options):
        if PortfolioSet.objects.filter(version=1).exists():
            self.stdout.write('v1 already exists')
            return

        assets = {symbol: get_asset(symbol, *spec) for symbol, spec in ASSETS.items()}
        portfolio_set = PortfolioSet.objects.create(version=1, is_active=True, published_at=timezone.now())

        for code, (profile, score, weights) in SEED.items():
            assert sum(weights.values()) == 100 and len(weights) == 3, code
            portfolio = Portfolio.objects.create(
                portfolio_set=portfolio_set, code=code, profile=profile, risk_score=score)
            PortfolioWeight.objects.bulk_create([
                PortfolioWeight(portfolio=portfolio, asset=assets[symbol], weight=Decimal(weight))
                for symbol, weight in weights.items()
            ])
        self.stdout.write('v1 created')