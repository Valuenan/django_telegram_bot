from asyncio import sleep
import datetime
import redis
import pickle

from django_telegram_bot.celery import app
from django_telegram_bot.settings import REDIS_HOST
from shop.models import Product
from shop.telegram.odata.data_exchange import import_images, import_category, import_products


@app.task
def load_images_task(load_all: bool = False, update: bool = False):
    global_result = {'time': datetime.datetime.now().strftime('%d-%m-%Y %H:%M'), 'updated': 0, 'created': 0,
                     'skipped': 0}
    if load_all:
        products = Product.objects.all().only('ref_key', 'name', 'image')
    else:
        products = Product.objects.filter(image=None).only('ref_key', 'name', 'image')
    for product in products:
        sleep(1)
        import_result = import_images(product, update)
        global_result[import_result] += 1
    r = redis.Redis(host=f'{REDIS_HOST[0]}', db=1)
    dict_bytes = pickle.dumps(global_result)
    r.mset({'message_load-image': dict_bytes})


@app.task
def load_category_task():
    time_start = datetime.datetime.now().strftime('%d-%m-%Y %H:%M')
    import_result = import_category()
    import_result['time'] = time_start
    r = redis.Redis(host=f'{REDIS_HOST[0]}', db=1)
    dict_bytes = pickle.dumps(import_result)
    r.mset({'message_load-category': dict_bytes})


@app.task
def load_products_task():
    time_start = datetime.datetime.now().strftime('%d-%m-%Y %H:%M')
    import_result = import_products()
    import_result['time'] = time_start
    r = redis.Redis(host=f'{REDIS_HOST[0]}', db=1)
    dict_bytes = pickle.dumps(import_result)
    r.mset({'message_load-products': dict_bytes})
