import os
import logging
from decimal import Decimal
import xlrd
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, LogoutView
from django.db import transaction, Error as DbError
from django.db.models import Count
from django.db.transaction import Error as TransactionError
from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages
from django.contrib.auth.models import User
from django.views.generic import ListView, DetailView

from odata.loader import create_request, CatalogFolder, CatalogProduct, ProductImage
from .forms import ImportGoodsForm
from users.models import Orders, Carts, Profile, OrderStatus, UserMessage
from .models import File, Category, Product, Rests, Shop, Image
from .telegram.bot import ready_order_message, send_message_to_user, manager_edit_order, manager_remove_order
from .telegram.settings import CREDENTIALS_1C

logger = logging.getLogger(__name__)


class ImportCategory1CView(View):
    @staticmethod
    def get(request):
        return render(request, 'admin/admin_import_from_1c.html')

    def post(self, request):
        created = 0
        updated = 0
        data = create_request(login=CREDENTIALS_1C['login'], password=CREDENTIALS_1C['password'], model=CatalogFolder,
                              server_url=CREDENTIALS_1C['server'], base=CREDENTIALS_1C['base'])
        for category in data:
            # Не принимаю группу 'XXX' и вложенные - это папка с мусором
            if 'd8915c68-29fd-11ee-a0fe-005056b6fe75' in [category.ref_key, category.parent_key]:
                continue
            exist_category = Category.objects.filter(id=category.search)
            if not exist_category:
                new_category = Category.objects.create(command=category.description.strip(), ref_key=category.ref_key,
                                                       id=category.search)
                if category.parent_key != '00000000-0000-0000-0000-000000000000':
                    parent_category = Category.objects.filter(ref_key=category.parent_key)
                    if parent_category:
                        new_category.parent_category = parent_category[0]
                        new_category.save()
                messages.add_message(request, messages.INFO, f'Создана категория {new_category.command}')
                created += 1
            else:
                exist_category = exist_category[0]
                new_parent_category = None

                if category.parent_key != '00000000-0000-0000-0000-000000000000':

                    parent_category = Category.objects.filter(ref_key=category.parent_key)
                    if parent_category:
                        new_parent_category = parent_category[0]
                    else:
                        continue
                if exist_category.parent_category == new_parent_category and exist_category.command == category.description.strip() and exist_category.ref_key == category.ref_key:
                    continue
                else:
                    exist_category.parent_category = new_parent_category
                    exist_category.command = category.description.strip()
                    exist_category.ref_key = category.ref_key
                    exist_category.save()
                    updated += 1
        messages.add_message(request, messages.INFO, f'Создано {created} категорий, обновленно {updated} категорий')
        return render(request, 'admin/admin_import_from_1c.html')


class ImportProducts1CView(View):

    @staticmethod
    def get(request):
        return render(request, 'admin/admin_import_from_1c.html')

    def post(self, request):
        created = 0
        updated = 0
        data = create_request(login=CREDENTIALS_1C['login'], password=CREDENTIALS_1C['password'], model=CatalogProduct,
                              server_url=CREDENTIALS_1C['server'], base=CREDENTIALS_1C['base'])
        for product in data:
            # Пропускаем товары в корне
            if '00000000-0000-0000-0000-000000000000' == product.parent_key:
                continue
            exist_product = Product.objects.filter(ref_key=product.ref_key)
            if not exist_product:

                category = Category.objects.filter(ref_key=product.parent_key)
                if category:
                    # TODO притянуть цену и в обновлении товара изменять цену
                    new_product = Product.objects.create(category=category[0], ref_key=product.ref_key,
                                                         name=product.name.strip(), price=0, search=product.search)
                    messages.add_message(request, messages.INFO, f'Создан товар {new_product.name}')
                else:
                    continue
                created += 1
            else:
                exist_product = exist_product[0]
                new_category = Category.objects.filter(ref_key=product.parent_key)
                if not new_category:
                    messages.add_message(request, messages.ERROR,
                                         f'Товар {product.name} был пропущен, отсутствует категория')
                    continue
                if exist_product.category == new_category[
                    0] and exist_product.ref_key == product.ref_key and exist_product.name == product.name.strip() and exist_product.search == product.search:
                    continue
                else:
                    exist_product.category = new_category[0]
                    exist_product.ref_key = product.ref_key
                    exist_product.name = product.name.strip()
                    exist_product.search = product.search
                    exist_product.save()
                    updated += 1
        messages.add_message(request, messages.INFO, f'Создано {created} товаров, обновленно {updated} товаров')
        return render(request, 'admin/admin_import_from_1c.html')


class ImportImages1CView(View):

    @staticmethod
    def get(request):
        return render(request, 'admin/admin_import_from_1c.html')

    def post(self, request):
        created = 0
        updated = 0
        skip = 0
        form = request.POST.copy()
        if 'load_all' in form.keys():
            products = Product.objects.all().only('ref_key', 'name', 'image')
        else:
            products = Product.objects.filter(image=None).only('ref_key', 'name', 'image')
        for product in products:
            if not product.ref_key:
                messages.add_message(request, messages.INFO,
                                     f'У товара {product.name} отсутсвует ссылка на 1с, поэтому будет пропущен')
                skip += 1
                continue
            image = create_request(login=CREDENTIALS_1C['login'], password=CREDENTIALS_1C['password'],
                                   model=ProductImage,
                                   server_url='clgl.1cbit.ru:10443/', base='470319099582-ut/',
                                   guid=product.ref_key)
            # Пропускаем при отсутвии фото
            if not image:
                skip += 1
                continue
            else:
                image = image[0]
            exist_image = Image.objects.filter(ref_key=image.ref_key)
            if not exist_image:
                image_link = Image.objects.create(name=f'{image.description.strip()}.{image.file_format.strip()}',
                                                  ref_key=image.ref_key)
                product.image = image_link
                product.save()
                created += 1
            elif 'update' in form.keys():
                exist_image = exist_image[0]
                exist_image.ref_key = image.ref_key
                exist_image.name = f'{image.description.strip()}.{image.file_format.strip()}'
                image_link = exist_image.save()
                product.image = image_link
                product.save()
                updated += 1
        messages.add_message(request, messages.INFO,
                             f'Создано {created} изображение товаров, обновленно {updated} изображений товаров, отсутсвуют фото у {skip} товаров')
        return render(request, 'admin/admin_import_from_1c.html')


def _relocate_duplicated_data(main_duplicate: object, main_duplicate_data: dict, duplicates: list) -> object:
    if ['red_key'] not in main_duplicate_data.values():
        for duplicate in duplicates:
            if duplicate.ref_key:
                main_duplicate.ref_key = duplicate.ref_key
    if ['image'] not in main_duplicate_data.values():
        for duplicate in duplicates:
            if duplicate.image:
                main_duplicate.image = duplicate.image
    if ['price'] not in main_duplicate_data.values():
        for duplicate in duplicates:
            if duplicate.price:
                main_duplicate.price = duplicate.price
    if ['search'] not in main_duplicate_data.values():
        for duplicate in duplicates:
            if duplicate.search:
                main_duplicate.search = duplicate.search
    if ['sale'] not in main_duplicate_data.values():
        for duplicate in duplicates:
            if duplicate.sale:
                main_duplicate.sale = duplicate.sale
    return main_duplicate


class RemoveDuplicates(View):

    @staticmethod
    def get(request):
        return render(request, 'admin/admin_import_from_1c.html')

    def post(self, request):
        conflicts = 0
        done = 0
        duplicates_data = Product.objects.values('name').annotate(name_count=Count('name')).filter(name_count__gt=1)
        for duplicate_data in duplicates_data:
            duplicates = Product.objects.filter(name=duplicate_data['name'])
            decision = {}
            main_duplicate = []
            main = 0
            for duplicate in duplicates:
                decision[duplicate] = {}
                if Rests.objects.filter(product=duplicate):
                    decision[duplicate]['rests'] = True
                if Carts.objects.filter(product=duplicate):
                    decision[duplicate]['cart'] = True
                if ['rests', 'cart'] in decision[duplicate].values():
                    decision[duplicate]['main'] = True
                    main_duplicate.append(duplicate)
                    main += 1
                if duplicate.ref_key:
                    decision[duplicate]['red_key'] = True
                if duplicate.image:
                    decision[duplicate]['image'] = True
                if duplicate.price != 0:
                    decision[duplicate]['price'] = True
                if duplicate.search:
                    decision[duplicate]['search'] = True
                if duplicate.sale is True:
                    decision[duplicate]['sale'] = True

            if main == 1:
                main_duplicate = main_duplicate[0]
                main_duplicate_data = decision.pop(main_duplicate, None)
                main_duplicate = _relocate_duplicated_data(main_duplicate, main_duplicate_data, duplicates)
                for duplicate, _ in decision.items():
                    duplicate.delete()
                main_duplicate.save()
                messages.add_message(request, messages.INFO,
                                     f'Товар {duplicate_data["name"]} дубли были убраны')
                done += 1

            if main > 1:
                conflicts += 1
                messages.add_message(request, messages.ERROR,
                                     f'Товар {duplicate_data["name"]} не смог решить конфликт, несколько дубликатов имеют связи корзинах или остатках')
            else:
                main_duplicate = duplicates[0]
                main_duplicate_data = decision.pop(main_duplicate, None)
                main_duplicate = _relocate_duplicated_data(main_duplicate, main_duplicate_data, duplicates)
                for duplicate, _ in decision.items():
                    duplicate.delete()
                main_duplicate.save()
                messages.add_message(request, messages.INFO,
                                     f'Товар {duplicate_data["name"]} дубли были убраны')
                done += 1
        messages.add_message(request, messages.INFO,
                             f'Удалось убрать дублей {done}, возникло {conflicts} конфликтов')
        return render(request, 'admin/admin_import_from_1c.html')


class RemoveNoRefKey(View):

    @staticmethod
    def get(request):
        return render(request, 'admin/admin_import_from_1c.html')

    def post(self, request):
        removed = 0
        conflicts = 0
        try:
            products = Product.objects.filter(ref_key=None)
            items = len(products)
            products.delete()
            messages.add_message(request, messages.INFO, f'Удалено {items} товаров без ссылки на 1с')
        except Exception:
            for product in products:
                try:
                    product.delete()
                    removed += 1
                except Exception as err:
                    messages.add_message(request, messages.ERROR, f'Товар {product.name}. Причина: {err}')
                    conflicts += 1
        messages.add_message(request, messages.INFO,
                             f'Удалено {removed} товаров без ссылки на 1с, не удалось {conflicts}')
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

                                    product_price = 0
                                    product_name = exel_data.cell_value(row, 0)
                                    product_code = int(exel_data.cell_value(row, 1).split('-')[-1])
                                    prachechniy_rests = exel_data.cell_value(row, 4)
                                    prachechniy_sum = exel_data.cell_value(row, 5)
                                    if prachechniy_rests != '':
                                        prachechniy_rests = Decimal(prachechniy_rests)
                                        prachechniy_sum = Decimal(prachechniy_sum)
                                        product_price = prachechniy_sum / prachechniy_rests
                                    else:
                                        prachechniy_rests = 0
                                    if product_price == 0:
                                        logger.error(f'import {file} error Bad values - {product_code}, rests = 0')
                                        log += f'import {file} error Bad values - {product_code}, rests = 0\n'
                                        messages.error(request,
                                                       f'Ошибка загрузки. Некорректные значения {product_code}, остаток = 0')
                                        break

                                    for_sale = lambda: False if product_name[-1] == '*' else True

                                    product = Product.objects.filter(search=product_code)

                                    if product:
                                        product = product[0]
                                        product.price = product_price
                                        product.sale = for_sale()
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
        return redirect(request.META.get('HTTP_REFERER'))
