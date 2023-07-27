import os
import logging
from decimal import Decimal
import xlrd
import csv
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
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
                    try:

                        with open(os.path.abspath(f'{settings.MEDIA_ROOT}/{file_for_import.file}')) as csvfile:
                            reader = csv.DictReader(csvfile)

                            for row in reader:
                                try:
                                    category_id, category_name, category_parent_id = list(row.values())[0].split(';')
                                    category_id = int(category_id.replace('"', ""))
                                    category_name = category_name.replace('"', "")
                                    category_parent_id = int(category_parent_id.replace('"', ""))

                                    if category_parent_id == 0:

                                        Category.objects.get_or_create(id=category_id, command=category_name)

                                    else:

                                        parent_category = Category.objects.filter(id=category_parent_id)
                                        category = Category.objects.filter(id=category_id)
                                        if not parent_category:
                                            temp_category = Category.objects.create(id=category_parent_id,
                                                                                    command="TEMP")
                                            temp_category.save()
                                            category = Category.objects.create(id=category_id, command=category_name,
                                                                               parent_category=temp_category)
                                            category.save()
                                        elif category:
                                            category = category[0]
                                            category.command = category_name
                                            category.parent_category = parent_category[0]
                                            category.save()
                                        elif not category:
                                            category = Category.objects.create(id=category_id, command=category_name,
                                                                               parent_category=parent_category[0])
                                            category.save()


                                except (ValueError, ZeroDivisionError) as ex:
                                    logger.error(f'import {file} error Bad values - {ex}')
                                    log += f'import {file} error Bad values - {ex}\n'
                                    messages.error(request, 'Error updating products. Bad values')

                        logger.info(f'import {file} - successfully')
                        log += f'import {file} - successfully\n'


                    except xlrd.XLRDError as ex:
                        logger.error(f'import {file} error Bad file - {ex}')
                        log += f'import {file} error Bad file - {ex}\n'
                        messages.error(request, 'Error updating products. Bad file')

        except TypeError as ex:
            logger.error(f'import error load file - {ex}')
            log += f'import error load file - {ex}'
            messages.error(request, 'Error load file')

        messages.success(request, 'Products updated successfully')
        return redirect('/admin/import_category/')


class ImportGoodsView(View):

    @staticmethod
    def get(request):
        file_form = ImportGoodsForm()
        return render(request, 'admin/admin_import_goods.html', context={'file_form': file_form})

    def post(self, request):
        log = ''
        user = User.objects.get(id=request.user.id)
        upload_file_form = ImportGoodsForm(request.POST, request.FILES)

        try:
            if upload_file_form.is_valid():
                files = request.FILES.getlist('file_field')

                for file in files:
                    file_for_import = File.objects.create(user=user, file=file)
                    try:
                        workbook = xlrd.open_workbook(os.path.abspath(f'{settings.MEDIA_ROOT}/{file_for_import.file}'))
                        exel_data = workbook.sheet_by_index(0)
                        shop = Shop.objects.get_or_create(name=exel_data.cell_value(0, 3))[0]
                        row = 3

                        while True:
                            try:
                                product_price = 0
                                product_name = exel_data.cell_value(row, 0)
                                product_image = exel_data.cell_value(row, 1)
                                product_category = exel_data.cell_value(row, 2)
                                prachechniy_rests = exel_data.cell_value(row, 3)
                                prachechniy_sum = exel_data.cell_value(row, 4)

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
                                                   f'Error updating products. Bad values {product_name}, rests = 0')
                                    break

                                category = Category.objects.filter(command=product_category.strip())

                                # Убираем товары с категорие Архив и без категории (по заданию Андрея)
                                if not category:
                                    row += 1
                                    continue

                                product = Product.objects.filter(name=product_name.strip())

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

                                row += 1
                            except IndexError:
                                logger.info(f'import {file} - successfully')
                                log += f'import {file} - successfully\n'
                                messages.success(request, 'Products updated successfully')
                                break
                            except (ValueError, ZeroDivisionError) as ex:
                                logger.error(f'import {file} error Bad values - {ex}')
                                log += f'import {file} error Bad values - {ex}\n'
                                messages.error(request, 'Error updating products. Bad values')

                    except xlrd.XLRDError as ex:
                        logger.error(f'import {file} error Bad file - {ex}')
                        log += f'import {file} error Bad file - {ex}\n'
                        messages.error(request, 'Error updating products. Bad file')

        except TypeError as ex:
            logger.error(f'import error load file - {ex}')
            log += f'import error load file - {ex}'
            messages.error(request, 'Error load file')
        return redirect('/admin/import_goods/')


class Login(LoginView):
    """Класс авторизации пользователя"""
    template_name = 'login.html'


class OrdersList(LoginRequiredMixin, ListView):
    login_url = '/login'
    model = Orders
    queryset = Orders.objects.exclude(status__in=[4, 5])
    context_object_name = 'orders'
    ordering = ['-date']


class OrderDetail(LoginRequiredMixin, DetailView):
    login_url = '/login'
    model = Orders
    context_object_name = 'order'

    def get_context_data(self, **kwargs):
        context = super(OrderDetail, self).get_context_data(**kwargs)
        self.model = self.model.objects.prefetch_related('carts_set').all()
        context['order_statuses'] = OrderStatus.objects.all()
        context['shops'] = Shop.objects.all().order_by('-id')
        return context

    def post(self, request, pk):
        form = request.POST.copy()
        _, new_status, shop = form.pop('csrfmiddlewaretoken'), form.pop('new_status')[0], int(form.pop('shop')[0])
        order = Orders.objects.get(id=pk)
        old_status = order.status.title
        rests_action = order.update_order_status(new_status)
        if new_status in ['0', '1', '2', '4']:
            order.update_order_quantity(form, rests_action, shop)
        elif new_status in ['3', '5']:
            ready_order_message(chat_id=order.profile.chat_id, order_id=order.id, order_sum=order.order_price)

        return redirect(f'/order/{pk}')
