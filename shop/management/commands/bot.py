from django.core.management.base import BaseCommand
from shop.telegram.bot import updater


class Command(BaseCommand):
    help = 'Запускате телеграм бота (магазин)'

    def handle(self, *args, **options):
        updater.start_polling()
