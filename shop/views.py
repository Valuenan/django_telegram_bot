import os
import logging
from decimal import Decimal
import xlrd
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib import messages
from django.contrib.auth.models import User
from django.views.generic import ListView, DetailView
from .forms import ImportGoodsForm
from users.models import Orders, Carts
from .models import File, Category, Product, Rests, Shop

logger = logging.getLogger(__name__)


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
                        shop_k = Shop.objects.get_or_create(name=exel_data.cell_value(0, 3))[0]
                        shop_p = Shop.objects.get_or_create(name=exel_data.cell_value(0, 5))[0]
                        row = 3

                        while True:
                            try:
                                product_price = 0
                                product_name = exel_data.cell_value(row, 0)
                                product_image = exel_data.cell_value(row, 1)
                                product_category = exel_data.cell_value(row, 2)
                                kievskaya_rests = exel_data.cell_value(row, 3)
                                kievskaya_sum = exel_data.cell_value(row, 4)
                                prachechniy_rests = exel_data.cell_value(row, 5)
                                prachechniy_sum = exel_data.cell_value(row, 6)

                                if product_image == ', ':
                                    product_image = 'no-image.jpg'
                                else:
                                    product_image = product_image.replace(', ', '.')

                                if kievskaya_rests != '':
                                    kievskaya_rests = Decimal(kievskaya_rests)
                                    kievskaya_sum = Decimal(kievskaya_sum)
                                    product_price = kievskaya_sum / kievskaya_rests
                                else:
                                    kievskaya_rests = 0
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

                                category = Category.objects.get_or_create(command=product_category)[0]

                                product = Product.objects.filter(name=product_name)

                                if product:
                                    product = product[0]
                                    product.category = category
                                    product.img = product_image
                                    product.price = product_price
                                    product.save()
                                    db_rests = Rests.objects.filter(product=product)
                                    for rest in db_rests:
                                        if rest.shop == shop_p:
                                            rest.amount = prachechniy_rests

                                        elif rest.shop == shop_k:
                                            rest.amount = kievskaya_rests
                                        rest.save()
                                else:
                                    product = Product.objects.create(name=product_name,
                                                                     category=category,
                                                                     img=product_image,
                                                                     price=product_price)
                                    product.save()
                                    db_rests = Rests.objects.create(shop=shop_p,
                                                                    product=product,
                                                                    amount=prachechniy_rests)
                                    db_rests.save()
                                    db_rests = Rests.objects.create(shop=shop_k,
                                                                    product=product,
                                                                    amount=kievskaya_rests)
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


class OrdersList(ListView):
    model = Orders
    queryset = Orders.objects.filter(soft_delete=False)
    context_object_name = 'orders'
    ordering = ['-date']


class OrderDetail(DetailView):
    model = Orders
    context_object_name = 'order'

    def get_context_data(self, **kwargs):
        context = super(OrderDetail, self).get_context_data(**kwargs)
        self.model = self.model.objects.prefetch_related('carts_set').all()
        return context

