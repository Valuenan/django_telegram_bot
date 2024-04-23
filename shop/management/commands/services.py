import datetime
from time import sleep

from django.core.management.base import BaseCommand

from shop.telegram.banking.banking_check import check_orders_payment
from shop.telegram.odata.data_exchange import auto_exchange
from shop.views import remove_no_order_carts

TIMER = 300
REMOVE_CARTS_TIME = datetime.time(hour=23, minute=54, second=0)


class Command(BaseCommand):
    help = 'Запускате проверку оплаты для бота'

    def handle(self, *args, **options):
        while True:
            check_orders_payment()
            remove_no_order_carts(REMOVE_CARTS_TIME)
            sleep(TIMER)
