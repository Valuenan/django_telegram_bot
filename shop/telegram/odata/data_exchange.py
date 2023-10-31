from datetime import datetime, timedelta

from django.contrib import messages
from django.db.models import Count

from shop.telegram.odata.loader import create_request, CatalogFolder, CatalogProduct, ProductImage, ProductPrice, \
    ProductAmount
from users.models import Carts
from shop.models import Category, Product, Rests, Shop, Image, RestsOdataLoad
from shop.telegram.settings import CREDENTIALS_1C

elimination_nomenclature = ['76577798-75bc-11eb-a0c1-005056b6fe75',
                            'a3b8770e-5c30-11ec-a0ca-005056b6fe75',
                            '0c9ffff5-1847-11ea-a082-005056b6fe75',
                            '5856a462-bf2d-11ec-a0cd-005056b6fe75',
                            '3e736a22-488f-11ed-a0d2-005056b6fe75',
                            '19a53e4d-f5cb-11e7-b10d-f068df5bef8b',
                            '07a53d7e-79f2-11ed-a1ff-be3af2b6059f',
                            '3e736a22-488f-11ed-a0d2-005056b6fe75',
                            '69dbf95a-3360-11ec-a0c9-005056b6fe75']



def import_category() -> list:
    """
    Загрузить категории из 1с
    :return: сообщения о результатах обмена
    """
    result_messages = []
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
            if category.parent_key != '00000000-0000-0000-0000-000000000000':
                parent_category = Category.objects.filter(ref_key=category.parent_key)
                if parent_category:
                    new_category = Category.objects.create(command=category.description.strip(),
                                                           ref_key=category.ref_key,
                                                           id=category.search, parent_category=parent_category[0])
                    result_messages.append((messages.INFO, f'Создана категория {new_category.command}'))
                    created += 1

            else:
                new_category = Category.objects.create(command=category.description.strip(),
                                                       ref_key=category.ref_key,
                                                       id=category.search)
                result_messages.append((messages.INFO, f'Создана категория {new_category.command}'))
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
    result_messages.append((messages.INFO, f'Создано {created} категорий, обновленно {updated} категорий'))
    if created != 0 or updated != 0:
        import_category()
    return result_messages


def import_products() -> list:
    """
    Загрузить товары из 1с
    :return: сообщения о результатах обмена
    """
    result_messages = []
    created = 0
    updated = 0
    data = create_request(login=CREDENTIALS_1C['login'], password=CREDENTIALS_1C['password'], model=CatalogProduct,
                          server_url=CREDENTIALS_1C['server'], base=CREDENTIALS_1C['base'])
    for product in data:
        exist_product = Product.objects.filter(ref_key=product.ref_key)
        if not exist_product:
            if product.name.strip()[-1] == '*':
                sale = False
            else:
                sale = True
            category = Category.objects.filter(ref_key=product.parent_key)
            if category:
                new_product = Product.objects.create(category=category[0], ref_key=product.ref_key, sale=sale,
                                                     name=product.name.strip(), price=0, search=product.search)
                result_messages.append((messages.INFO, f'Создан товар {new_product.name}'))
            else:
                continue
            created += 1
        else:
            exist_product = exist_product[0]
            if exist_product.name[-1] == '*':
                sale = False
            else:
                sale = True
            new_category = Category.objects.filter(ref_key=product.parent_key)
            if not new_category:
                result_messages.append((messages.ERROR, f'Товар {product.name} был пропущен, отсутствует категория'))
                continue
            if exist_product.category == new_category[
                0] and exist_product.ref_key == product.ref_key and exist_product.name == product.name.strip() and exist_product.search == product.search and exist_product.sale == sale:
                continue
            else:
                exist_product.category = new_category[0]
                exist_product.ref_key = product.ref_key
                exist_product.name = product.name.strip()
                exist_product.search = product.search
                exist_product.sale = sale
                exist_product.save()
                updated += 1
    result_messages.append((messages.INFO, f'Создано {created} товаров, обновленно {updated} товаров'))
    return result_messages


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
    last_data = RestsOdataLoad.objects.last()
    if not year or not month or not day:
        if not last_data:
            load_date = datetime.now()
        else:
            load_date = last_data.date_time - timedelta(days=1)
        year = load_date.year
        month = load_date.month
        day = load_date.day
    up_to_date = datetime.now() + timedelta(days=1)

    while True:
        data = create_request(login=CREDENTIALS_1C['login'], password=CREDENTIALS_1C['password'],
                              model=ProductAmount,
                              server_url='clgl.1cbit.ru:10443/', base='470319099582-ut/', year=year,
                              month=month, day=day)
        for rest in data:
            exist_rest = RestsOdataLoad.objects.filter(recorder=rest.recorder, product_key=rest.product_key)

            if not exist_rest:
                if rest.active:
                    db_rest = Rests.objects.filter(product__ref_key=rest.product_key)
                    if db_rest:
                        db_rest = db_rest[0]
                        if rest.record_type == 'Expense':
                            rest.change_quantity *= -1
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
                            # Пропуск номенклатуры "Пакет, Тестовый товар, карточки акций"
                            if rest.product_key in elimination_nomenclature:
                                continue
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
                                              product_key=rest.product_key)
                create += 1
            else:
                exist_rest = exist_rest[0]
                if exist_rest.active == rest.active:
                    continue
                else:
                    product = Product.objects.filter(ref_key=rest.product_key)
                    if not product:
                        # Пропуск номенклатуры "Пакет"
                        if rest.product_key == '76577798-75bc-11eb-a0c1-005056b6fe75':
                            continue
                        result_messages.append((messages.ERROR,
                                                f'Ошибка: Отсутсвует товар {rest.product_key}. Сначала загрузите товары. Товар был пропущен'))
                        continue
                    if rest.record_type == 'Receipt':
                        rest.change_quantity *= -1
                    db_rest = Rests.objects.filter(product__ref_key=rest.product_key)[0]
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


def import_images(load_all: bool = False, update: bool = False) -> list:
    """
    Загрузить изображения из 1с
    :param load_all: если параметр False, будут загружены фото только у номенклатуры у которой отсутвуют
    :param update: разрешить обновлять фото в номенклатуре
    :return: сообщения о результатах обмена
    """
    result_messages = []
    created = 0
    updated = 0
    skip = 0
    if load_all:
        products = Product.objects.all().only('ref_key', 'name', 'image')
    else:
        products = Product.objects.filter(image=None).only('ref_key', 'name', 'image')
    for product in products:
        if not product.ref_key:
            result_messages.append((messages.INFO,
                                    f'У товара {product.name} отсутсвует ссылка на 1с, поэтому будет пропущен'))
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
        elif update:
            exist_image = exist_image[0]
            exist_image.ref_key = image.ref_key
            exist_image.name = f'{image.description.strip()}.{image.file_format.strip()}'
            image_link = exist_image.save()
            product.image = image_link
            product.save()
            updated += 1
    result_messages.append((messages.INFO,
                            f'Создано {created} изображение товаров, обновленно {updated} изображений товаров, отсутсвуют фото у {skip} товаров'))
    return result_messages


def mark_sale():
    products = Product.objects.all()
    for product in products:
        if product.name[-1] == '*':
            product.sale = False
            product.save()
        else:
            product.sale = True
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
