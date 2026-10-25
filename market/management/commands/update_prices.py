from django.core.management.base import BaseCommand
from market.services import update_all_prices


class Command(BaseCommand):

    def handle(self, *args, **options):
        for symbol,ok in update_all_prices().items():
            self.stdout.write(f'{symbol}: {"OK" if ok else "FAILED"}')