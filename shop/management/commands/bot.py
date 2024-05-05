from django.core.management.base import BaseCommand
from shop.telegram.bot import updater
from shop.telegram.settings import WEBHOOK_PORT, WEBHOOK, WEBHOOK_URL
import os

PORT = int(os.environ.get('PORT', WEBHOOK_PORT))


class Command(BaseCommand):
    help = 'Запускате телеграм бота (магазин)'

    def handle(self, *args, **options):
        if WEBHOOK:

            updater.start_webhook(
                listen='127.0.0.1',
                port=PORT,
                webhook_url=WEBHOOK_URL
            )
            updater.idle()

        else:
            updater.start_polling()
