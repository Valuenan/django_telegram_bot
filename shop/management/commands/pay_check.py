from time import sleep

from django.core.management.base import BaseCommand

from shop.telegram.banking_check import check_orders_payment

TIMER = 900


class Command(BaseCommand):
    help = 'Запускате проверку оплаты для бота'
    session = None

    def handle(self, *args, **options):
        while True:
            check_orders_payment()
            sleep(TIMER)
