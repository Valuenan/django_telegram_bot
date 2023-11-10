import os
import logging
import pickle
from decimal import Decimal
import xlrd
import redis
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages
from django.contrib.auth.models import User
from django.views.generic import ListView, DetailView
from django_telegram_bot.settings import BASE_DIR, REDIS_HOST

from .forms import ImportGoodsForm
from users.models import Orders, Profile, OrderStatus, UserMessage
from .models import File, Product, Rests, Shop
from .telegram.bot import ready_order_message, manager_edit_order, manager_remove_order
from .telegram.odata.data_exchange import import_prices, import_rests, remove_duplicates, remove_no_ref_key, mark_sale
from .tasks import load_images_task, load_category_task, load_products_task, send_everyone_task
from .utilities import _send_message_to_user

logger = logging.getLogger(__name__)

load_task_tags = {"message_load-image": "Загрузка фотографий",
                  "message_load-category": "Загрузка категорий",
                  "message_load-products": "Загрузка номенклатуры",
                  "message_send-everyone": "Отправка сообщений"}


def _add_messages(request, messages_info: list):
    for message_type, message in messages_info:
        messages.add_message(request, message_type, message)


class ImportCategory1CView(View):
    @staticmethod
    def get(request):
        r = redis.Redis(host=f'{REDIS_HOST[0]}', db=1)
        for message_tag in load_task_tags.keys():
            dict_bytes = r.get(message_tag)
            if dict_bytes:
                loads = pickle.loads(dict_bytes)
                if message_tag == "message_send-everyone":
                    progress = 'в процессе'
                    print(loads['complete'])
                    if loads['complete']:
                        r.delete(message_tag)
                        progress = 'выполнена'
                    message = f'{loads["time"]}. {load_task_tags[message_tag]} {progress}. Пользователей к рассылке: {loads["all"]} -  отправлено: {loads["success"]}, пропущено: {loads["error"]}'
                else:
                    r.delete(message_tag)
                    message = f'{loads["time"]}. {load_task_tags[message_tag]} выполнена. Создано: {loads["created"]}, обновлено: {loads["updated"]}, пропущено: {loads["skipped"]}'
                messages.add_message(request, messages.INFO, message)

        return render(request, 'admin/admin_import_from_1c.html')

    def post(self, request):
        messages.add_message(request, messages.INFO, 'Загрузка категорий...')
        load_category_task.delay()
        return redirect('load_from_1c')


class ImportProducts1CView(View):

    @staticmethod
    def get(request):
        return render(request, 'admin/admin_import_from_1c.html')

    def post(self, request):
        messages.add_message(request, messages.INFO, 'Загрузка номенклатуры...')
        load_products_task.delay()
        return redirect('load_from_1c')


class ImportPrices1CView(View):

    @staticmethod
    def get(request):
        return render(request, 'admin/admin_import_from_1c.html')

    def post(self, request):
        form = request.POST.copy()
        load_all = False
        if 'load_all' in form.keys():
            load_all = True
        result_messages = import_prices(load_all=load_all)
        _add_messages(request, result_messages)
        return render(request, 'admin/admin_import_from_1c.html')


class ImportRests1CView(View):

    @staticmethod
    def get(request):
        return render(request, 'admin/admin_import_from_1c.html')

    def post(self, request):
        result_messages = import_rests()
        _add_messages(request, result_messages)
        return render(request, 'admin/admin_import_from_1c.html')


class ImportImages1CView(View):

    @staticmethod
    def get(request):
        return render(request, 'admin/admin_import_from_1c.html')

    def post(self, request):
        messages.add_message(request, messages.INFO, 'Загрузка изображений товаров...')
        form = request.POST.copy()
        load_all, update = False, False
        if 'load_all' in form.keys():
            load_all = True
        if 'update' in form.keys():
            update = True
        load_images_task.delay(load_all, update)
        return redirect('load_from_1c')


class MarkProductsSale(View):

    @staticmethod
    def get(request):
        return render(request, 'admin/admin_import_from_1c.html')

    def post(self, request):
        result_messages = mark_sale()
        _add_messages(request, result_messages)
        return render(request, 'admin/admin_import_from_1c.html')


class RemoveDuplicates(View):

    @staticmethod
    def get(request):
        return render(request, 'admin/admin_import_from_1c.html')

    def post(self, request):
        result_messages = remove_duplicates()
        _add_messages(request, result_messages)
        return render(request, 'admin/admin_import_from_1c.html')


class RemoveNoRefKey(View):

    @staticmethod
    def get(request):
        return render(request, 'admin/admin_import_from_1c.html')

    def post(self, request):
        result_messages = remove_no_ref_key()
        _add_messages(request, result_messages)
        return render(request, 'admin/admin_import_from_1c.html')


class ImportGoodsView(View):

    @staticmethod
    def get(request):
        file_form = ImportGoodsForm()
        return render(request, 'admin/admin_import_goods.html', context={'file_form': file_form})

    def post(self, request):
        log = ''
        user = User.objects.get(id=request.user.id)
        upload_file_form = ImportGoodsForm(request.POST, request.FILES)
        wrong_group_products = []

        rests = Rests.objects.exclude(amount=0)

        if rests:

            for rest in rests:
                rest.amount = 0
                rest.save()

            Rests.objects.bulk_update(rests, ['amount', ])

        try:
            if upload_file_form.is_valid():
                files = request.FILES.getlist('file_field')
                for file in files:
                    file_for_import = File.objects.create(user=user, file=file)
                    try:
                        with xlrd.open_workbook(
                                os.path.abspath(f'{settings.MEDIA_ROOT}/{file_for_import.file}')) as workbook:

                            exel_data = workbook.sheet_by_index(0)
                            shop = Shop.objects.get_or_create(name=exel_data.cell_value(0, 4))[0]
                            try:
                                for row in range(3, exel_data.nrows - 1):

                                    product_name = exel_data.cell_value(row, 1).strip()
                                    prachechniy_rests = exel_data.cell_value(row, 4)

                                    product = Product.objects.filter(name=product_name)

                                    if product:
                                        product = product[0]
                                        product.save()
                                        db_rests = Rests.objects.filter(product=product, shop=shop)
                                        if db_rests:
                                            for rest in db_rests:
                                                rest.amount = prachechniy_rests
                                                rest.save()
                                        else:
                                            Rests.objects.create(shop=shop,
                                                                 product=product,
                                                                 amount=prachechniy_rests)
                                    else:
                                        wrong_group_products.append(product_name)

                            except (ValueError, ZeroDivisionError) as ex:
                                logger.error(f'import {file} error Bad values - {ex}')
                                log += f'import {file} error Bad values - {ex}\n'
                                messages.error(request, 'Ошибка загрузки. Некорректные значения')

                    except xlrd.XLRDError as ex:
                        logger.error(f'import {file} error Bad file - {ex}')
                        log += f'import {file} error Bad file - {ex}\n'
                        messages.error(request, 'Ошибка загрузки. Некорректный файл')

        except TypeError as ex:
            logger.error(f'import error load file - {ex}')
            log += f'import error load file - {ex}'
            messages.error(request, 'Ошибка загрузки')

        messages.success(request, f'Товары загружены, кроме: {wrong_group_products}')
        return redirect('/admin/import_goods/')


class Login(LoginView):
    """Класс авторизации пользователя"""
    template_name = 'login.html'


class Logout(LogoutView):
    """Класс, позволяющий разлогинить пользователя"""
    template_name = 'login.html'


class Product_data:
    def __init__(self, name):
        self.info_color = 'green'
        self.name = name


class PhotoCheckList(View):
    login_url = '/login'

    def get(self, request):
        missing_photos = []
        rests = Rests.objects.exclude(amount=0).only('product')
        for rest in rests:
            product = rest.product
            if product.image is None:
                continue
            try:
                with open(f'{BASE_DIR}/static/products/{product.image}'):
                    pass
            except FileNotFoundError:
                missing_photos.append(product)

        return render(request, 'admin/photo_checklist.html', context={'missing_photos': missing_photos})


class ProductsCheckList(View):
    login_url = '/login'

    def get(self, request):
        file_form = ImportGoodsForm()
        return render(request, 'admin/products_checklist.html', context={'file_form': file_form})

    def post(self, request):
        post_data = request.POST.copy()
        if 'remove_good' in post_data:
            remove_good = True
        else:
            remove_good = False
        upload_file_form = ImportGoodsForm(request.POST, request.FILES)
        user = User.objects.get(id=request.user.id)
        products = []
        try:
            if upload_file_form.is_valid():
                files = request.FILES.getlist('file_field')
                for file in files:
                    file_for_import = File.objects.create(user=user, file=file)
                    try:
                        with xlrd.open_workbook(
                                os.path.abspath(f'{settings.MEDIA_ROOT}/{file_for_import.file}')) as workbook:

                            exel_data = workbook.sheet_by_index(0)
                            db_products = Product.objects.all().only('price')
                            rests_bot = Rests.objects.all().exclude(amount=0)

                            try:
                                for row in range(3, exel_data.nrows - 1):
                                    product = Product_data(exel_data.cell_value(row, 1).strip())
                                    product.rest_1c = int(exel_data.cell_value(row, 4))
                                    product.price_1c = int(exel_data.cell_value(row, 5) // product.rest_1c)

                                    product_bot_info = db_products.filter(name=product.name)

                                    if product_bot_info:
                                        product.price_bot = int(product_bot_info[0].price)
                                        if product.price_1c != product.price_bot:
                                            product.info_color = 'red'
                                        product_bot_rests = product_bot_info[0].rests_set.all()
                                        if product_bot_rests:
                                            product_bot_rests = product_bot_rests[0]
                                            rests_bot = rests_bot.exclude(product=product_bot_rests.product)
                                            product.rest_bot = int(product_bot_rests.amount)
                                            if product.rest_1c != product.rest_bot:
                                                product.info_color = 'red'
                                        else:
                                            if product.info_color != 'red':
                                                product.info_color = 'orange'
                                            product.rest_bot = 'нет'
                                    else:
                                        product.info_color = 'orange'
                                        product.price_bot = 'нет'
                                        product.rest_bot = 'нет'

                                    if remove_good and product.info_color == 'green':
                                        continue

                                    products.append(product)
                                for rest in rests_bot:
                                    product = Product_data(rest.product.name)
                                    product.rest_1c = 'нет'
                                    product.price_1c = 'нет'
                                    product.info_color = 'red'
                                    product.price_bot = rest.product.price
                                    product.rest_bot = rest.amount
                                    products.append(product)

                            except (ValueError, ZeroDivisionError) as ex:
                                logger.error(f'import {file} error Bad values - {ex}')
                                messages.error(request, 'Ошибка загрузки. Некорректные значения')

                    except xlrd.XLRDError as ex:
                        logger.error(f'import {file} error Bad file - {ex}')
                        messages.error(request, 'Ошибка загрузки. Некорректный файл')

        except TypeError as ex:
            logger.error(f'import error load file - {ex}')
            messages.error(request, 'Ошибка загрузки')
        file_form = ImportGoodsForm()
        return render(request, 'admin/products_checklist.html', context={'file_form': file_form, 'products': products})


class OrdersList(LoginRequiredMixin, ListView):
    login_url = '/login'
    model = Orders
    queryset = Orders.objects.exclude(status__in=[6, 7])
    context_object_name = 'orders'
    ordering = ['id']

    def get_context_data(self, **kwargs):
        context = super(OrdersList, self).get_context_data(**kwargs)
        users = Profile.objects.values('phone')
        context['count_users'] = users.count()
        context['count_users_phone'] = users.exclude(phone=None).count()
        context['new_message'] = UserMessage.objects.filter(checked=False)
        return context


class OrdersHistory(LoginRequiredMixin, ListView):
    login_url = '/login'
    model = Orders
    queryset = Orders.objects.filter(status__in=[6, 7])
    context_object_name = 'orders'
    ordering = ['id']

    def get_context_data(self, **kwargs):
        context = super(OrdersHistory, self).get_context_data(**kwargs)
        context['new_message'] = UserMessage.objects.filter(checked=False)
        return context


class OrderDetail(LoginRequiredMixin, DetailView):
    login_url = '/login'
    model = Orders
    context_object_name = 'order'

    def get_context_data(self, **kwargs):
        context = super(OrderDetail, self).get_context_data(**kwargs)
        self.model = self.model.objects.prefetch_related('carts_set').all()
        context['products'] = context['order'].carts_set.all()
        context['order_sum'] = context['order'].delivery_price
        if context['order'].discount < Decimal(1):
            for cart in context['products']:
                if cart.product.sale:
                    new_price = round(cart.product.price * context['order'].discount)
                    cart.product.price = new_price
                context['order_sum'] += round(cart.product.price * cart.amount, 2)
        else:
            for cart in context['products']:
                context['order_sum'] += round(cart.product.price * cart.amount, 2)

        if context['object'].deliver:
            context['order_statuses'] = OrderStatus.objects.exclude(id='5')
        else:
            context['order_statuses'] = OrderStatus.objects.exclude(id='4')
        context['shops'] = Shop.objects.all().order_by('-id')
        context['new_message'] = UserMessage.objects.filter(checked=False)

        return context

    def post(self, request, pk):
        form = request.POST.copy()

        _, new_status, shop = form.pop('csrfmiddlewaretoken'), form.pop('new_status')[0], int(form.pop('shop')[0])

        order = Orders.objects.get(id=pk)

        if 'delivery_price' in form:
            delivery_price = int(form.pop('delivery_price')[0])
            order.delivery_price = delivery_price
        else:
            delivery_price = order.delivery_price
        if 'tracing_num' in form and form['tracing_num'] != 'None':
            tracing_num = form.pop('tracing_num')[0]
            order.tracing_num = tracing_num
            order.save()
        elif 'tracing_num' in form:
            form.pop('tracing_num')
        if 'delivery_info' in form and form['delivery_info'] != '':
            delivery_info = form.pop('delivery_info')[0]
            order.delivery_info = delivery_info
            order.save()
        elif 'delivery_info' in form:
            form.pop('delivery_info')

        order.admin_check = request.user
        old_status = order.status.title
        rests_action = order.update_order_status(new_status)

        order_sum = delivery_price
        carts = order.carts_set.filter(soft_delete=False)
        if order.discount < Decimal(1):
            for cart in carts:
                if cart.product.sale:
                    order_sum += round(cart.product.price * order.discount) * int(cart.amount)
                else:
                    order_sum += cart.product.price * int(cart.amount)
        else:
            for cart in carts:
                order_sum += round(cart.product.price * cart.amount, 2)

        if new_status == '0':
            order.update_order_quantity(form, rests_action, shop)
            result = manager_edit_order(order)
            message = f'Данные схранены, статус изменен. {result}'
        elif new_status == '2':
            order.update_order_quantity(form, rests_action, shop)
            message = 'Данные схранены, статус изменен'
        elif new_status == '5':
            try:
                manager_remove_order(order)
                message = 'Данные схранены, статус изменен'
            except Exception as err:
                message = f'Неудалось удалить сообщение из канала поп причине: {err}'
                messages.add_message(request, messages.ERROR, message)
        elif new_status in ['1', '3', '4', '6'] and old_status != new_status:
            if new_status == '6':
                try:
                    manager_remove_order(order)
                    message = 'Заявка удалена из канала менеджеров'
                    messages.add_message(request, messages.INFO, message)
                except Exception as err:
                    err_message = f'Неудалось удалить сообщение из канала поп причине: {err}'
                    messages.add_message(request, messages.ERROR, err_message)
            status, result = ready_order_message(chat_id=order.profile.chat_id, order_id=order.id,
                                                 order_sum=int(order_sum),
                                                 status=new_status, deliver=order.deliver,
                                                 delivery_price=delivery_price,
                                                 pay_type=order.payment.title,
                                                 tracing_num=order.tracing_num, payment_url=order.payment_url)

            if status == 'ok':
                message = f'Данные схранены, статус изменен, отправлено сообщение: {result}'
            else:
                message = f'Ошибка: {result}'
                messages.add_message(request, messages.ERROR, message)
                order.update_order_status(old_status)
                return redirect(f'/order/{pk}')

        else:
            message = 'Данные схранены'
        messages.add_message(request, messages.INFO, message)
        return redirect(f'/order/{pk}')


class SendMessageToUser(LoginRequiredMixin, View):
    login_url = '/login'

    def post(self, request):
        form = request.POST.copy()
        user_chat_id = Profile.objects.get(chat_id=form['chat_id'])
        messages_not_checked = UserMessage.objects.filter(user=user_chat_id, checked=False)
        if messages_not_checked:
            messages_not_checked.update(checked=True)
        result = _send_message_to_user(form, user_chat_id=user_chat_id, manager=request.user)
        if result[0] == 'error':
            messages.error(request, result[1])
        else:
            messages.success(request, result[1])
        return redirect(request.META.get('HTTP_REFERER'))


class UsersMessagesList(LoginRequiredMixin, ListView):
    login_url = '/login'
    model = UserMessage
    queryset = UserMessage.objects.filter(checked=False).order_by('user')
    context_object_name = 'users'
    template_name = 'users/messages_list.html'

    def get_context_data(self, **kwargs):
        context = super(UsersMessagesList, self).get_context_data(**kwargs)
        context['new_message'] = UserMessage.objects.filter(checked=False)
        return context


class UsersMessagesDetail(LoginRequiredMixin, View):
    login_url = '/login'
    model = UserMessage
    context_object_name = 'user_messages'

    def get(self, request, pk):
        user = Profile.objects.get(chat_id=pk)
        user_messages = UserMessage.objects.filter(user=user)
        new_message = self.model.objects.filter(checked=False)
        return render(request, 'users/messages_detail.html',
                      context={'user_messages': user_messages, 'new_message': new_message, 'pk': pk})


class SendMessageToEveryone(LoginRequiredMixin, View):
    login_url = '/login'

    def get(self, request):
        new_message = UserMessage.objects.filter(checked=False)
        return render(request, 'users/send_everyone.html', context={'new_message': new_message})

    def post(self, request):
        messages.add_message(request, messages.INFO, 'Начал рассылку...')
        form = dict(request.POST.copy())
        users_ids = Profile.objects.all().values('chat_id')
        users_ids = list(users_ids)
        send_everyone_task.delay(form, users_ids)
        return redirect(request.META.get('HTTP_REFERER'))
