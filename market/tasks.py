from celery import shared_task
from celery.signals import worker_ready
from .services import update_all_prices

@shared_task(name='market.update_prices')
def update_prices_task():
    return update_all_prices()

@worker_ready.connect
def fill_price_on_startup(sender, **kwargs):
    update_prices_task.delay()