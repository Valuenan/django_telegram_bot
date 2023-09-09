import os
import logging
from decimal import Decimal
import xlrd
import csv
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, LogoutView
from django.db import transaction, Error as DbError
from django.db.transaction import Error as TransactionError
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib import messages
from django.contrib.auth.models import User
from django.views.generic import ListView, DetailView
from .forms import ImportGoodsForm, ImportCategoryForm
from users.models import Orders, Carts, Profile, OrderStatus, UserMessage
from .models import File, Category, Product, Rests, Shop
from .telegram.bot import ready_order_message, send_message_to_user

logger = logging.getLogger(__name__)


class ImportCategoryView(View):

    @staticmethod
    def get(request):
        file_form = ImportCategoryForm()
        return render(request, 'admin/admin_import_category.html', context={'file_form': file_form})

    def post(self, request):
        log = ''
        user = User.objects.get(id=request.user.id)
        upload_file_form = ImportCategoryForm(request.POST, request.FILES)

        try:
            if upload_file_form.is_valid():
                files = request.FILES.getlist('file_field')
                for file in files:

                    file_for_import = File.objects.create(user=user, file=file)

                    with open(os.path.abspath(f'{settings.MEDIA_ROOT}/{file_for_import.file}'),
                              encoding='cp1251') as csvfile:
                        reader = csv.reader(csvfile)

                        for row in reader:
                            try:
                                category_id, category_name, category_parent_id = row[0].split(';')
                                if category_id == 'Id':
                                    continue

                                category_id = int(category_id.replace('"', "")[-5:])
                                category_name = category_name.replace('"', "")
                                category_parent_id = int(category_parent_id.replace('"', "")[-5:])

                                category = Category.objects.filter(id=category_id,
                                                                   parent_category=category_parent_id)
                                if category:
                                    category.update(command=category_name)
                                else:

                                    if category_parent_id == 0:
                                        Category.objects.get_or_create(id=category_id, command=category_name)

                                    else:

                                        parent_category = Category.objects.filter(id=category_parent_id)
                                        category = Category.objects.filter(id=category_id)
                                        if not parent_category:
                                            temp_category = Category.objects.create(id=category_parent_id,
                                                                                    command="TEMP")
                                            temp_category.save()
                                            category = Category.objects.create(id=category_id,
                                                                               command=category_name,
                                                                               parent_category=temp_category)
                                            category.save()
                                        elif category:
                                            category = category[0]
                                            category.command = category_name
                                            category.parent_category = parent_category[0]
                                            category.save()
                                        elif not category:
                                            category = Category.objects.create(id=category_id,
                                                                               command=category_name,
                                                                               parent_category=parent_category[0])
                                            category.save()

                            except (ValueError, ZeroDivisionError) as ex:
                                logger.error(f'import {file} error Bad values - {ex}')
                                log += f'import {file} error Bad values - {ex}\n'
                                messages.error(request, 'Ошибка загрузки. Некорректные значения')

                        logger.info(f'import {file} - successfully')
                        log += f'import {file} - successfully\n'

        except TypeError as ex:
            logger.error(f'import error load file - {ex}')
            log += f'import error load file - {ex}'
            messages.error(request, 'Ошибка загрузки')

        messages.success(request, 'Category updated successfully')
        return redirect('/admin/import_category/')


# def _unicode_csv_reader(utf8_data, dialect=csv.excel, **kwargs):
#     csv_reader = csv.reader(utf8_data, dialect=dialect, **kwargs)
#     for row in csv_reader:
#         yield [unicode(cell, 'utf-8') for cell in row]


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

            for i in range(len(rests)):
                rests[i].amount = 0

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

                                    product_price = 0
                                    product_name = exel_data.cell_value(row, 1)
                                    product_image = exel_data.cell_value(row, 2)
                                    product_category = exel_data.cell_value(row, 3)
                                    prachechniy_rests = exel_data.cell_value(row, 4)
                                    prachechniy_sum = exel_data.cell_value(row, 5)

                                    if product_category == '':
                                        product_category = 0
                                    else:
                                        product_category = int(product_category)

                                    if product_image == ', ':
                                        product_image = 'no-image.jpg'
                                    else:
                                        product_image = product_image.replace(', ', '.')

                                    if prachechniy_rests != '':
                                        prachechniy_rests = Decimal(prachechniy_rests)
                                        prachechniy_sum = Decimal(prachechniy_sum)
                                        product_price = prachechniy_sum / prachechniy_rests
                                    else:
                                        prachechniy_rests = 0
                                    if product_price == 0:
                                        logger.error(f'import {file} error Bad values - {product_name}, rests = 0')
                                        log += f'import {file} error Bad values - {product_name}, rests = 0\n'
                                        messages.error(request,
                                                       f'Ошибка загрузки. Некорректные значения {product_name}, остаток = 0')
                                        break
                                    category = Category.objects.filter(id=product_category)

                                    # Убираем товары с категорие Архив и без категории (по заданию Андрея)
                                    if not category:
                                        wrong_group_products.append(product_name)
                                        continue

                                    product = Product.objects.filter(name=product_name)

                                    if product:
                                        product = product[0]
                                        product.category = category[0]
                                        product.img = product_image
                                        product.price = product_price
                                        product.save()
                                        db_rests = Rests.objects.filter(product=product)
                                        for rest in db_rests:
                                            rest.amount = prachechniy_rests
                                            rest.save()
                                    else:
                                        product = Product.objects.create(name=product_name,
                                                                         category=category[0],
                                                                         img=product_image,
                                                                         price=product_price)
                                        product.save()
                                        db_rests = Rests.objects.create(shop=shop,
                                                                        product=product,
                                                                        amount=prachechniy_rests)
                                        db_rests.save()

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
        if context['object'].deliver:
            context['order_statuses'] = OrderStatus.objects.exclude(id='5')
        else:
            context['order_statuses'] = OrderStatus.objects.exclude(id='4')
        context['order_sum'] = context['order'].order_price + context['order'].delivery_price
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
        order_sum = order.order_price + delivery_price
        if new_status in ['0', '2', '5']:
            order.update_order_quantity(form, rests_action, shop)
        elif new_status in ['1', '3', '4', '6'] and old_status != new_status:
            ready_order_message(chat_id=order.profile.chat_id, order_id=order.id, order_sum=int(order_sum),
                                status=new_status, delivery_price=delivery_price, pay_type=order.payment.title,
                                tracing_num=order.tracing_num)

        return redirect(f'/order/{pk}')


def _send_message_to_user(request, form, user_chat_id, everyone=False):
    if 'disable_notification' in form:
        disable_notification = True
    else:
        disable_notification = False

    try:

        if form['message'] and not everyone:
            UserMessage.objects.create(user=user_chat_id, manager=request.user, message=form['message'],
                                       checked=True)
            user_chat_id = user_chat_id.chat_id
        result, text = send_message_to_user(chat_id=user_chat_id, message=form['message'],
                                            disable_notification=disable_notification)

        if result == 'ok' and not everyone:
            messages.success(request, text)
        elif result == 'ok' and everyone:
            pass
        else:
            messages.error(request,
                           f'Сообщение не отправлено пользователю ид {user_chat_id}, {text}. Обратитесь к администратору')

    except (DbError, TransactionError) as error:
        messages.error(request, f'Возникла ошибка ид пользователя {user_chat_id}, {error}. Обратитесь к администратору')


class SendMessageToUser(LoginRequiredMixin, View):
    login_url = '/login'

    def post(self, request):
        form = request.POST.copy()
        user_chat_id = Profile.objects.get(chat_id=form['chat_id'])
        messages_not_checked = UserMessage.objects.filter(user=user_chat_id, checked=False)
        if messages_not_checked:
            messages_not_checked.update(checked=True)
        _send_message_to_user(request, form, user_chat_id)
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
        form = request.POST.copy()
        users_ids = Profile.objects.all().values('chat_id')
        for user_chat_id in users_ids:
            _send_message_to_user(request, form, user_chat_id['chat_id'], everyone=True)
        if not list(messages.get_messages(request)):
            messages.success(request, 'Все сообщения были отправленны')
        return render(request, 'users/send_everyone.html')
