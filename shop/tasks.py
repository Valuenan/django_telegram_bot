from asyncio import sleep

from django_telegram_bot.celery import app
from shop.models import Product
from shop.telegram.odata.data_exchange import import_images



@app.task
def load_images_task(load_all: bool = False, update: bool = False):
    if load_all:
        products = Product.objects.all().only('ref_key', 'name', 'image')
    else:
        products = Product.objects.filter(image=None).only('ref_key', 'name', 'image')
    for product in products:
        sleep(1)
        import_images(product, update)


