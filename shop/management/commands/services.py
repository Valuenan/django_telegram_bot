from time import sleep

from django.core.management.base import BaseCommand

from shop.telegram.banking.banking_check import check_orders_payment
from shop.telegram.odata.data_exchange import auto_exchange
from shop.views import _add_messages

TIMER = 300


class Command(BaseCommand):
    help = 'Запускате проверку оплаты для бота'
    session = None

    def handle(self, *args, **options):
        while True:
            check_orders_payment()
            auto_exchange()
            sleep(TIMER)
