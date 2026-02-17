from time import sleep
import datetime
import redis
import pickle

from django_telegram_bot.celery import app
from django_telegram_bot.settings import REDIS_HOST
from shop.models import Product, Rests, Shop
from shop.telegram.odata.data_exchange import import_images, import_category, import_products, import_prices, \
    import_rests, mark_sale
from shop.utilities import _send_message_to_user


@app.task
def load_images_task(load_all: bool = False, update: bool = False):
    global_result = {'time': datetime.datetime.now().strftime('%d-%m-%Y %H:%M'), 'updated': 0, 'created': 0,
                     'skipped': 0}
    if load_all:
        products = Product.objects.all().only('ref_key', 'name', 'image')
    else:
        products = Product.objects.filter(image=None).only('ref_key', 'name', 'image')
    for product in products:
        import_result = import_images(product, update)
        global_result[import_result] += 1
    r = redis.Redis(host=f'{REDIS_HOST}', db=1)
    dict_bytes = pickle.dumps(global_result)
    r.mset({'message_load-image': dict_bytes})


@app.task
def load_category_task():
    time_start = datetime.datetime.now().strftime('%d-%m-%Y %H:%M')
    import_result = import_category()
    import_result['time'] = time_start
    r = redis.Redis(host=f'{REDIS_HOST}', db=1)
    dict_bytes = pickle.dumps(import_result)
    r.mset({'message_load-category': dict_bytes})


@app.task
def load_products_task():
    time_start = datetime.datetime.now().strftime('%d-%m-%Y %H:%M')
    import_result = import_products()
    mark_sale()
    import_result['time'] = time_start
    r = redis.Redis(host=f'{REDIS_HOST}', db=1)
    dict_bytes = pickle.dumps(import_result)
    r.mset({'message_load-products': dict_bytes})


@app.task
def load_prices_task(load_all: bool = False):
    time_start = datetime.datetime.now().strftime('%d-%m-%Y %H:%M')
    import_result = import_prices(load_all=load_all)
    import_result['time'] = time_start
    r = redis.Redis(host=f'{REDIS_HOST}', db=1)
    dict_bytes = pickle.dumps(import_result)
    r.mset({'message_load-prices': dict_bytes})


@app.task
def load_rests_task():
    time_start = datetime.datetime.now().strftime('%d-%m-%Y %H:%M')
    import_result = import_rests()
    products_no_rests = Product.objects.filter(rests__isnull=True)
    shop = Shop.objects.get(id=1)
    for product in products_no_rests:
        Rests.objects.create(product=product, shop=shop, amount=0)
    import_result['time'] = time_start
    r = redis.Redis(host=f'{REDIS_HOST}', db=1)
    dict_bytes = pickle.dumps(import_result)
    r.mset({'message_load-rests': dict_bytes})


@app.task
def send_everyone_task(form, users_ids):
    time_start = datetime.datetime.now().strftime('%d-%m-%Y %H:%M')
    complete_result = {'time': time_start, 'success': 0, 'error': 0, 'all': len(users_ids), 'complete': False}
    r = redis.Redis(host=f'{REDIS_HOST}', db=1)

    for user_chat_id in users_ids:
        result = _send_message_to_user(form, user_chat_id=user_chat_id['chat_id'], everyone=True)
        complete_result[result[0]] += 1
        dict_bytes = pickle.dumps(complete_result)
        r.mset({'message_send-everyone': dict_bytes})
        sleep(1)
    complete_result['complete'] = True
    dict_bytes = pickle.dumps(complete_result)
    r.mset({'message_send-everyone': dict_bytes})
