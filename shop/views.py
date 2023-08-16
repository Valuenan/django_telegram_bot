import os
import logging
from decimal import Decimal
import xlrd
import csv
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib import messages
from django.contrib.auth.models import User
from django.views.generic import ListView, DetailView
from .forms import ImportGoodsForm, ImportCategoryForm
from users.models import Orders, Carts, Profile, OrderStatus
from .models import File, Category, Product, Rests, Shop
from .telegram.bot import ready_order_message

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

                    with open(os.path.abspath(f'{settings.MEDIA_ROOT}/{file_for_import.file}'), encoding='cp1251') as csvfile:
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


def _unicode_csv_reader(utf8_data, dialect=csv.excel, **kwargs):
    csv_reader = csv.reader(utf8_data, dialect=dialect, **kwargs)
    for row in csv_reader:
        yield [unicode(cell, 'utf-8') for cell in row]


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
    queryset = Orders.objects.exclude(status__in=[5, 6])
    context_object_name = 'orders'
    ordering = ['id']


class OrdersHistory(LoginRequiredMixin, ListView):
    login_url = '/login'
    model = Orders
    queryset = Orders.objects.filter(status__in=[5, 6])
    context_object_name = 'orders'
    ordering = ['id']


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
        order.admin_check = request.user
        old_status = order.status.title
        rests_action = order.update_order_status(new_status)
        order_sum = order.order_price + delivery_price
        if new_status in ['0', '2', '5']:
            order.update_order_quantity(form, rests_action, shop)
        elif new_status in ['1', '3', '4', '6'] and old_status != new_status:
            ready_order_message(chat_id=order.profile.chat_id, order_id=order.id, order_sum=int(order_sum),
                                status=new_status, delivery_price=delivery_price)

        return redirect(f'/order/{pk}')
