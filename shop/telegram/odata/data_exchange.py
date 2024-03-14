from datetime import datetime, timedelta

from django.contrib.auth.models import User
from django.db import close_old_connections, connection

from django.contrib import messages
from django.db.models import Count

from shop.telegram.odata.loader import create_request, CatalogFolder, CatalogProduct, ProductImage, ProductPrice, \
    ProductAmount
from users.models import Carts, Profile
from shop.models import Category, Product, Rests, Shop, Image, RestsOdataLoad, DiscountGroup
from shop.telegram.settings import CREDENTIALS_1C


def import_category() -> dict:
    """
    Загрузить категории из 1с
    :return: результаты обмена
    """
    result = {'created': 0, 'updated': 0, 'skipped': 0}
    data = create_request(login=CREDENTIALS_1C['login'], password=CREDENTIALS_1C['password'], model=CatalogFolder,
                          server_url=CREDENTIALS_1C['server'], base=CREDENTIALS_1C['base'])
    categories_visible = list(Category.objects.filter(hide=False))
    for category in data:
        # Не принимаю группу 'XXX' и вложенные - это папка с мусором
        if 'd8915c68-29fd-11ee-a0fe-005056b6fe75' in [category.ref_key, category.parent_key]:
            continue
        close_old_connections()
        connection.ensure_connection()
        exist_category = Category.objects.filter(id=category.search)
        if not exist_category:
            if category.parent_key != '00000000-0000-0000-0000-000000000000':
                parent_category = Category.objects.filter(ref_key=category.parent_key)
                if parent_category:
                    Category.objects.create(command=category.description.strip(),
                                            ref_key=category.ref_key,
                                            id=category.search, parent_category=parent_category[0])
                    result['created'] += 1

            else:
                Category.objects.create(command=category.description.strip(),
                                        ref_key=category.ref_key,
                                        id=category.search)
                result['created'] += 1
        else:
            exist_category = exist_category[0]
            if exist_category in categories_visible:
                categories_visible.remove(exist_category)
            new_parent_category = None
            if category.parent_key != '00000000-0000-0000-0000-000000000000':
                parent_category = Category.objects.filter(ref_key=category.parent_key)
                if parent_category:
                    new_parent_category = parent_category[0]
                else:
                    continue
            if exist_category.hide or exist_category.parent_category != new_parent_category or exist_category.command != category.description.strip() or exist_category.ref_key != category.ref_key:
                exist_category.hide = False
                exist_category.parent_category = new_parent_category
                exist_category.command = category.description.strip()
                exist_category.ref_key = category.ref_key
                exist_category.save()
                result['updated'] += 1
    if categories_visible:
        for category_hide in categories_visible:
            category_hide.hide = True
            category_hide.save()
            result['updated'] += 1
    if result['created'] != 0 or result['updated'] != 0:
        add_result = import_category()
        result['created'] += add_result['created']
        result['updated'] += add_result['updated']
    return result


def import_products() -> dict:
    """
    Загрузить товары из 1с
    :return: результаты обмена
    """
    result = {'created': 0, 'updated': 0, 'skipped': 0}
    data = create_request(login=CREDENTIALS_1C['login'], password=CREDENTIALS_1C['password'], model=CatalogProduct,
                          server_url=CREDENTIALS_1C['server'], base=CREDENTIALS_1C['base'])
    close_old_connections()
    connection.ensure_connection()
    for product in data:
        exist_product = Product.objects.filter(ref_key=product.ref_key)
        if not exist_product:
            if product.parent_key != '00000000-0000-0000-0000-000000000000':
                category = Category.objects.filter(ref_key=product.parent_key)
            else:
                category = [None]
            if category:
                Product.objects.create(category=category[0], ref_key=product.ref_key, name=product.name.strip(),
                                       price=0, search=product.search)
            else:
                continue
            result['created'] += 1
        else:
            exist_product = exist_product[0]
            if product.parent_key != '00000000-0000-0000-0000-000000000000':
                new_category = Category.objects.filter(ref_key=product.parent_key)
                if not new_category:
                    result['skipped'] += 1
                    continue
            else:
                new_category = [None]

            if exist_product.category != new_category[
                0] or exist_product.ref_key != product.ref_key or exist_product.name != product.name.strip() or exist_product.search != product.search:
                exist_product.category = new_category[0]
                exist_product.ref_key = product.ref_key
                exist_product.name = product.name.strip()
                exist_product.search = product.search
                exist_product.save()
                result['updated'] += 1
    return result


def import_prices(year: datetime = None, month: datetime = None, load_all: bool = False) -> list:
    """
    Загрузить цены из 1с
    ! Oбязательно должны быть переданы оба параметра иначе загружаться данные на текущий месяц !
    :param year: год установки цен
    :param month: месяц установки цен
    :param load_all: загрузить все цены (если True параметры передаваемые в year и month игнорируются)
    :return: сообщения о результатах обмена
    """
    result_messages = []
    update = 0
    skip = 0
    if not year or not month:
        now = datetime.now()
        year = now.year
        month = now.month
    data = create_request(login=CREDENTIALS_1C['login'], password=CREDENTIALS_1C['password'], model=ProductPrice,
                          server_url='clgl.1cbit.ru:10443/', base='470319099582-ut/',
                          guid='9eae0ae2-50d8-11e6-b065-91bcc12f28ea', load_all=load_all, year=year, month=month)
    for price in data:
        exist_product = Product.objects.filter(ref_key=price.product_key)
        if not exist_product:
            skip += 1
            continue
        else:
            update += 1
            exist_product = exist_product[0]
            exist_product.price = price.price
            exist_product.save()
    result_messages.append(
        (messages.INFO, f'Цены были обновлены у {update} товаров, не удалось обновить цены у {skip} товаров'))
    return result_messages


def import_rests(year: datetime = None, month: datetime = None, day: datetime = None) -> list:
    result_messages = []
    create = 0
    update = 0
    conflict = 0
    last_data = RestsOdataLoad.objects.exclude(recorder=None).latest('date_time')
    not_linked_odata_records = RestsOdataLoad.objects.filter(recorder=None)

    if not year or not month or not day:
        if not last_data:
            load_date = datetime.now()
        else:
            load_date = last_data.date_time - timedelta(days=1)
    up_to_date = datetime.now() + timedelta(days=1)

    while True:
        year = load_date.year
        month = load_date.month
        day = load_date.day
        data = create_request(login=CREDENTIALS_1C['login'], password=CREDENTIALS_1C['password'],
                              model=ProductAmount,
                              server_url='clgl.1cbit.ru:10443/', base='470319099582-ut/', year=year,
                              month=month, day=day)
        for rest in data:
            exist_rest = RestsOdataLoad.objects.filter(recorder=rest.recorder, product_key=rest.product_key,
                                                       line_number=rest.line_number)
            if not exist_rest:
                if rest.active:
                    # Добавляем ссылку на документ 1с - если товар был продан через бота
                    add_link = not_linked_odata_records.filter(product_key=rest.product_key,
                                                               amount=rest.change_quantity)
                    if add_link and rest.record_type == 'Expense':
                        add_link = add_link[0]
                        add_link.recorder = rest.recorder
                        add_link.date_time = rest.date_time
                        add_link.line_number = rest.line_number
                        add_link.save()
                        not_linked_odata_records = not_linked_odata_records.filter(recorder=None)
                        continue
                    db_rest = Rests.objects.filter(product__ref_key=rest.product_key)
                    if db_rest:
                        db_rest = db_rest[0]
                        if rest.record_type == 'Expense':
                            db_rest.amount += rest.change_quantity * -1
                        else:
                            db_rest.amount += rest.change_quantity
                        if db_rest.amount >= 0:
                            db_rest.save()
                        else:
                            product = Product.objects.filter(ref_key=rest.product_key)[0]
                            result_messages.append((messages.ERROR,
                                                    f'Ошибка: Не достаточно товара {product.name} для списания, конечный остаток {db_rest.amount}'))
                            conflict += 1
                            continue
                    else:
                        product = Product.objects.filter(ref_key=rest.product_key)
                        if not product:
                            result_messages.append((messages.ERROR,
                                                    f'Ошибка: Отсутсвует товар {rest.product_key}. Сначала загрузите товары. Товар был пропущен'))
                            continue
                        if rest.record_type == 'Receipt':
                            shop = Shop.objects.all()[0]
                            Rests.objects.create(shop=shop, product=product[0], amount=rest.change_quantity)
                        else:
                            result_messages.append((messages.ERROR,
                                                    f'Ошибка: Попытка списания товара {product[0].name} без остатков'))
                            conflict += 1
                            continue
                RestsOdataLoad.objects.create(active=rest.active, date_time=rest.date_time, recorder=rest.recorder,
                                              product_key=rest.product_key, amount=rest.change_quantity,
                                              line_number=rest.line_number)
                create += 1
            else:
                exist_rest = exist_rest[0]
                if exist_rest.active == rest.active:
                    continue
                else:
                    product = Product.objects.filter(ref_key=rest.product_key)
                    if not product:
                        result_messages.append((messages.ERROR,
                                                f'Ошибка: Отсутсвует товар {rest.product_key}. Сначала загрузите товары. Товар был пропущен'))
                        continue
                    db_rest = Rests.objects.filter(product__ref_key=rest.product_key)[0]
                    if rest.record_type == 'Receipt':
                        db_rest.amount += rest.change_quantity * -1
                    else:
                        db_rest.amount += rest.change_quantity
                    if db_rest.amount >= 0:
                        db_rest.save()
                    else:
                        result_messages.append((messages.ERROR,
                                                f'Ошибка: Не достаточно товара {product[0].name} для отмены получения'))
                        conflict += 1
                        continue
                    exist_rest.active = rest.active
                    exist_rest.save()
                    update += 1
        if load_date.month == up_to_date.month and load_date.day == up_to_date.day:
            break
        load_date += timedelta(days=1)
    result_messages.append((messages.INFO,
                            f'Были обновлены остатки {update} товаров, создано {create} остатков, конфликтов {conflict}'))
    return result_messages


def import_images(product: Product, update: bool):
    """
    Загрузить изображения из 1с
    :param load_all: если параметр False, будут загружены фото только у номенклатуры у которой отсутвуют
    :param update: разрешить обновлять фото в номенклатуре
    """
    image = create_request(login=CREDENTIALS_1C['login'], password=CREDENTIALS_1C['password'],
                           model=ProductImage,
                           server_url='clgl.1cbit.ru:10443/', base='470319099582-ut/',
                           guid=product.ref_key)
    # Пропускаем при отсутвии фото
    if image:
        close_old_connections()
        connection.ensure_connection()
        if type(image) == list:
            image = image[0]
        exist_image = Image.objects.filter(ref_key=image.ref_key)
        if not exist_image:
            image_link = Image.objects.create(name=f'{image.description.strip()}.{image.file_format.strip()}',
                                              ref_key=image.ref_key)
            product.image = image_link
            product.save()
            return 'created'
        elif update:
            exist_image = exist_image[0]
            exist_image.ref_key = image.ref_key
            exist_image.name = f'{image.description.strip()}.{image.file_format.strip()}'
            exist_image.save()
            product.image = exist_image
            product.save()
            return 'updated'
    return 'skipped'


def mark_sale():
    """
    Выдать группу скидок товарам, согласно тригеру
    """

    products = Product.objects.all()
    discounts = DiscountGroup.objects.all()
    discount_groups = {}
    for discount in discounts:
        discount_groups[discount.trigger] = discount
    for product in products:
        if product.name[-1] in discount_groups.keys():
            product.discount_group = discount_groups[product.name[-1]]
            product.save()
        else:
            product.discount_group = discount_groups['Def']
            product.save()


def _relocate_duplicated_data(main_duplicate: object, main_duplicate_data: dict, duplicates: list) -> object:
    """
    Перенос данных в основной дупликат
    :param main_duplicate: основной дупликат
    :param main_duplicate_data: данные основного дупликата
    :param duplicates: другие дупликаты
    :return: возвращает основной дупликат с собранными данными из других если это поле было не заполненно
    """
    main_duplicate_keys = main_duplicate_data.keys()
    if 'rests' not in main_duplicate_keys:
        for duplicate in duplicates:
            rest = Rests.objects.filter(product=duplicate)
            if rest:
                rest = rest[0]
                rest.product = main_duplicate
                rest.save()
    if 'red_key' not in main_duplicate_keys:
        for duplicate in duplicates:
            if duplicate.ref_key:
                main_duplicate.ref_key = duplicate.ref_key
    if 'image' not in main_duplicate_keys:
        for duplicate in duplicates:
            if duplicate.image:
                main_duplicate.image = duplicate.image
    if 'price' not in main_duplicate_keys:
        for duplicate in duplicates:
            if duplicate.price:
                main_duplicate.price = duplicate.price
    if 'search' not in main_duplicate_keys:
        for duplicate in duplicates:
            if duplicate.search:
                main_duplicate.search = duplicate.search
    if 'sale' not in main_duplicate_keys:
        for duplicate in duplicates:
            if duplicate.sale:
                main_duplicate.sale = duplicate.sale
    return main_duplicate


def remove_duplicates() -> list:
    """
    Удалить дубли в базе бота
    :return: сообщения о результатах обмена
    """
    result_messages = []
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
            if 'cart' in decision or 'rests' in decision:
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
            result_messages.append((messages.INFO,
                                    f'Товар {duplicate_data["name"]} дубли были убраны'))
            done += 1
        elif main > 1:
            conflicts += 1
            result_messages.append((messages.ERROR,
                                    f'Товар {duplicate_data["name"]} не смог решить конфликт, несколько дубликатов имеют связи корзинах или остатках'))
        else:
            main_duplicate = duplicates[0]
            main_duplicate_data = decision.pop(main_duplicate, None)
            main_duplicate = _relocate_duplicated_data(main_duplicate, main_duplicate_data, duplicates)
            for duplicate, _ in decision.items():
                duplicate.delete()
            main_duplicate.save()
            result_messages.append((messages.INFO,
                                    f'Товар {duplicate_data["name"]} дубли были убраны'))
            done += 1
    result_messages.append((messages.INFO,
                            f'Удалось убрать дублей {done}, возникло {conflicts} конфликтов'))
    return result_messages


def remove_no_ref_key() -> list:
    """
    Удалить номенклатуру без ссылки на 1с (ref_key)
    :return: сообщения о результатах обмена
    """
    result_messages = []
    removed = 0
    conflicts = 0
    try:
        products = Product.objects.filter(ref_key=None)
        items = len(products)
        products.delete()
        result_messages.append((messages.INFO, f'Удалено {items} товаров без ссылки на 1с'))
    except Exception:
        for product in products:
            try:
                product.delete()
                removed += 1
            except Exception as err:
                result_messages.append((messages.ERROR, f'Товар {product.name}. Причина: {err}'))
                conflicts += 1
    result_messages.append((messages.INFO, f'Удалено {removed} товаров без ссылки на 1с, не удалось {conflicts}'))
    return result_messages


def edit_users_profile() -> list:
    """
    Переместить имя и фамилию пользователя бота из User в Profile
    Удалить User модель для пользователя бота
    :return: сообщения о результатах обмена
    """
    result_messages = []
    users = User.objects.exclude(is_staff=True)

    for user in users:
        try:
            profile = Profile.objects.filter(user=user)
            if profile:
                profile.update(user=None, first_name=user.first_name, last_name=user.last_name)
            else:
                Profile.objects.create(user=None, first_name=user.first_name, last_name=user.last_name, chat_id=user.username)
            user.delete()
        except Exception as err:
            user_name = str(user.username)
            result_messages.append((messages.ERROR, f'{user_name=}, {err=}'))

    result_messages.append((messages.INFO, 'Измененения были внесены'))
    return result_messages


def auto_exchange():
    """Выполнить авто обмен с1"""
    all_results_messages = []

    # Загрузка категорий
    all_results_messages.append(import_category())

    # Загрузка изменений цен за последний месяц (и товаров если отсутсвуют в базе)
    result_messages = import_prices()
    for messages_type, _ in result_messages:
        if messages_type == messages.ERROR:
            all_results_messages.append(import_products())
            all_results_messages.append(import_prices())
        else:
            all_results_messages.append(result_messages)

    # Загрузка изменений остатков на текущий день (и товаров если отсутсвуют в базе)
    result_messages = import_rests()
    for messages_type, _ in result_messages:
        if messages_type == messages.ERROR:
            all_results_messages.append(import_products())
            all_results_messages.append(import_rests())
        else:
            all_results_messages.append(result_messages)

    # Оставляем только сообщения с ошибками
    index = 0
    while index != len(all_results_messages):
        if all_results_messages[index][0] == messages.INFO:
            all_results_messages.pop(index)
        else:
            index += 1
    return all_results_messages
