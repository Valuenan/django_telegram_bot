from datetime import datetime

import mysql.connector
from mysql.connector import Error

from django_telegram_bot.settings import DATABASES

ADMIN_TG = '@Ottuda_SPB_help'
PRODUCTS_PAGINATION_NUM = 5
DATABASE = DATABASES['default']['NAME']
HOST = DATABASES['default']['HOST']
DB_USER = DATABASES['default']['USER']
BD_PASSWORD = DATABASES['default']['PASSWORD']
BD_PORT = DATABASES['default']['PORT']


def connect_db(sql_request: str) -> object:
    try:
        connection = mysql.connector.connect(host=HOST,
                                             database=DATABASE,
                                             user=DATABASE,
                                             password=BD_PASSWORD)
        if connection.is_connected():
            cursor = connection.cursor()
            cursor.execute(sql_request)
            return connection, cursor
    except Error as e:
        print("Error while connecting to MySQL", e)


def _id_to_name(table: str, ids: list) -> list:
    names = []

    for item_id in ids:
        db, cur = connect_db(f"SELECT name FROM {table} WHERE id='{item_id}'")
        names.append(cur.fetchone())
        cur.close()
        db.close()
    return names


def check_user_is_staff(chat_id: int) -> (str or None):
    db, cur = connect_db(f"""SELECT is_staff FROM auth_user 
    INNER JOIN profile ON auth_user.id = profile.user_id
    WHERE chat_id='{chat_id}'""")
    is_staff = cur.fetchone()
    cur.close()
    db.close()
    return is_staff


def start_user(first_name: str, last_name: str, username: str, chat_id: int, cart_message_id: int,
               discount: int) -> (
        str, str):
    """Запись новых пользователей"""
    db, cur = connect_db(f"""SELECT auth_user.id, profile.phone
    FROM auth_user
    INNER JOIN profile ON auth_user.id = profile.user_id
    WHERE username='{chat_id}'""")
    data = cur.fetchall()
    if data:
        user_id, user_phone = data[0]
    else:
        user_id, user_phone = None, None
    cur.close()
    db.close()

    if user_id is None:
        try:
            db, cur = connect_db(f"""INSERT INTO auth_user (first_name, last_name, username, is_staff, is_superuser, is_active, email, password, date_joined) 
            VALUES ('{first_name}', '{last_name}', '{chat_id}','0', '0','1', 'user@email.ru' ,'UserPassword333', CURRENT_TIMESTAMP)""")
            db.commit()
            db, cur = connect_db(f"""INSERT INTO profile (user_id, telegram_name, chat_id, cart_message_id, discount, delivery) 
            SELECT auth_user.id, '{username}', '{chat_id}', '{cart_message_id}', '{discount}', '0'
            FROM auth_user WHERE auth_user.username = '{chat_id}'""")
            db.commit()
            cur.close()
            db.close()

            text = f'''Добро пожаловать в телеграм магазин "OTTUDA"
            
При возникновении проблем обратитесь в канал 👉 {ADMIN_TG} или <b> напишите сообщение в бота </b> (сообщение будет доставлено нашим менеджерам).

Все команды для работы с ботом находятся в "меню", кнопка "меню" находится левее строки ввода сообщений.
Вы можете ознакомиться с инструкциями по работе с ботом 👉 /info 

Так же вы можете подписаться на наш информационный канал 👉 <a href="https://t.me/+hjgE01JrL1I2ZDQy">FinEst_333</a>, где мы публикуем информацию о товарах и скидках.

Добро пожаловать {first_name}, для оформления заказов нужно указать номер телефона. Отправьте в чат номер телефона (формат +7** или 8**).'''
            status = 'new_user'
        except Exception as err:
            text = f'''Извините {first_name} произошла ошибка, попробуйте еще раз нажать 👉 /start.
Если ошибка повторяется, обратитесь за помощью в канал {ADMIN_TG}'''
            status = err
    elif user_phone is None:
        text = f'''Добро пожаловать {first_name}, нужно указать номер телефона. Отправьте в чат номер телефона. (формат +7*** или 8***)'''
        status = 'no-phone'
    else:
        text, status = f'''Добро пожаловать {first_name}.
Вы можете ознакомиться с инструкциями по работе с ботом по ссылке 👉 /info ''', 'ok'

    return text, status


def user_add_phone(chat_id: int, phone_num: str):
    """Записать номер телефона пользователя"""
    db, cur = connect_db(f"""UPDATE profile SET phone='{phone_num}' WHERE chat_id='{chat_id}'""")
    db.commit()
    cur.close()
    db.close()


def get_shops() -> list:
    """Получить список магазинов"""
    db, cur = connect_db(f"SELECT id, name FROM shops")
    shops = cur.fetchall()
    cur.close()
    db.close()
    return shops


def get_category(category_id: int = None) -> list:
    """Получить список категорй"""
    if category_id is not None:
        db, cur = connect_db(
            f"SELECT command, id, parent_category_id FROM categories WHERE parent_category_id='{category_id}'")
        categories = cur.fetchall()
        db, cur = connect_db(f"SELECT command FROM categories WHERE id='{category_id}'")
        this_category_name = cur.fetchone()
        cur.close()
        db.close()
        return categories, this_category_name
    else:
        db, cur = connect_db("SELECT command, id, parent_category_id FROM categories WHERE parent_category_id is NULL")
        categories = cur.fetchall()
        cur.close()
        db.close()
        return categories


def get_parent_category_id(category_id: int) -> list:
    """ Получить родительскую категорию """
    db, cur = connect_db(
        f"SELECT parent_category_id FROM categories WHERE id='{category_id}'")
    parent_category_id = cur.fetchone()
    cur.close()
    db.close()
    return parent_category_id


def get_products(chosen_category: int, page: int) -> (list, int):
    """Получить список товаров и пагинация"""
    db, cur = connect_db((f"""
    SELECT products.id, products.name, image.name, products.price, products.category_id, products.sale, sum(rests.amount) AS rest
    FROM products 
    INNER JOIN rests ON products.id = rests.product_id
    LEFT JOIN image ON image.id = products.image_id
    WHERE category_id='{chosen_category}' AND rests.amount > 0
    GROUP BY products.id
    ORDER BY products.id"""))
    products = cur.fetchall()
    cur.close()
    db.close()
    if len(products) > PRODUCTS_PAGINATION_NUM:
        count_pages = (len(products) - 1) // PRODUCTS_PAGINATION_NUM
        start = page * PRODUCTS_PAGINATION_NUM
        end = start + PRODUCTS_PAGINATION_NUM
        return products[start: end], count_pages
    else:
        return products, None


def get_product_id(product_name: str) -> list:
    """Получить ид товара"""
    db, cur = connect_db(f"SELECT id FROM products WHERE name='{product_name}'")
    request = cur.fetchone()
    cur.close()
    db.close()
    return request


def edit_to_cart(command: str, chat_id: int, product_id: int) -> (int, list):
    """Добавить/Удалить товар из корзины"""
    db, cur = connect_db(f"""SELECT id FROM profile WHERE chat_id='{chat_id}'""")
    profile_id = cur.fetchone()[0]

    db, cur = connect_db(f"""SELECT amount FROM carts 
    WHERE carts.profile_id='{profile_id}' AND carts.product_id='{product_id}' AND carts.order_id IS NULL""")
    product_info = cur.fetchone()
    db, cur = connect_db(f"""SELECT products.price, SUM(rests.amount) AS rest_sum FROM products 
            INNER JOIN rests on products.id = rests.product_id
            WHERE products.id={product_id}
            GROUP BY products.id""")
    product_price, product_rests = cur.fetchall()[0]
    if product_info is None and command == 'add' or product_info is None and command == 'add-cart':
        db, cur = connect_db(
            f"""INSERT INTO carts (profile_id, product_id, amount, price, soft_delete) 
            VALUES ('{profile_id}', '{product_id}', '1', '{product_price}', '0')""")
        amount = 1
    elif product_info is None and command == 'remove':
        amount = 0
    else:
        amount = product_info[0]
        if command == 'get':
            pass
        elif command == 'add' or command == 'add-cart':
            if amount < product_rests:
                amount += + 1
        elif command == 'remove' or command == 'remove-cart':
            amount -= 1
        else:
            amount = 0
        if amount == 0:
            db, cur = connect_db(f"""DELETE FROM carts
            WHERE carts.profile_id = '{profile_id}' AND carts.product_id='{product_id}' AND carts.order_id IS NULL""")
        else:
            db, cur = connect_db(f"""UPDATE carts SET amount='{amount}'
            WHERE carts.profile_id = '{profile_id}' AND carts.product_id='{product_id}' AND carts.order_id IS NULL""")
    db.commit()
    db, cur = connect_db(f"SELECT name FROM products WHERE id='{product_id}'")
    product = cur.fetchone()
    cur.close()
    db.close()
    return amount, product, product_rests


def old_cart_message_to_none(chat_id: int):
    """Id открытой корзины переставить в None"""
    db, cur = connect_db(f"UPDATE profile SET cart_message_id='0' WHERE chat_id='{chat_id}'")
    db.commit()
    cur.close()
    db.close()


def old_cart_message(chat_id) -> (int or None):
    """Получение id сообщения корзины в базе наличия открытой корзины"""
    db, cur = connect_db(f"SELECT cart_message_id FROM profile WHERE chat_id='{chat_id}'")
    cart_message_id = cur.fetchone()
    db.commit()
    cur.close()
    db.close()
    if cart_message_id == 0:
        return cart_message_id
    else:
        return cart_message_id[0]


def show_cart(chat_id: int) -> list:
    """Получить список товаров в корзине"""
    db, cur = connect_db(f"""SELECT products.name, products.sale, carts.amount, carts.price
    FROM carts  
    INNER JOIN products 
    ON carts.product_id = products.id 
    WHERE carts.order_id IS NULL AND carts.profile_id = (SELECT id FROM profile where chat_id='{chat_id}') AND carts.soft_delete = '0'""")
    cart_info = cur.fetchall()
    if cart_info is None:
        cart_list = []
    else:
        cart_list = cart_info
    cur.close()
    db.close()
    return cart_list


def save_cart_message_id(chat_id: int, cart_message_id: int):
    """Сохраняет id сообщения с корзиной"""
    db, cur = connect_db(f"UPDATE profile SET cart_message_id='{cart_message_id}' WHERE chat_id='{chat_id}'")
    db.commit()
    cur.close()
    db.close()


def db_delete_cart(chat_id: int):
    """Удалить корзину"""
    db, cur = connect_db(f"""DELETE FROM carts 
    WHERE order_id IS NULL AND profile_id=(SELECT id FROM profile WHERE chat_id='{chat_id}')""")
    db.commit()
    db, cur = connect_db(f"UPDATE profile SET cart_message_id='0' WHERE chat_id='{chat_id}'")
    db.commit()
    cur.close()
    db.close()


def edit_profile(value: bool or str, field: str, chat_id: int):
    """Сохранить настроки доставки"""
    try:
        db, cur = connect_db(f"UPDATE profile SET {field}='{value}' WHERE chat_id='{chat_id}'")
        db.commit()
        cur.close()
        db.close()
        return True
    except TypeError:
        return False


def edit_user(chat_id: int, field: str, value: str) -> bool:
    """Изменить профиль"""
    try:
        db, cur = connect_db(f"UPDATE auth_user SET {field}='{value}' WHERE username='{chat_id}'")
        db.commit()
        cur.close()
        db.close()
        return True
    except TypeError:
        return False


def get_user_profile(chat_id: int) -> tuple:
    """Получить профиль пользователя"""
    db, cur = connect_db(f"""SELECT auth_user.first_name, auth_user.last_name, profile.phone, profile.delivery_street
        FROM profile 
        INNER JOIN auth_user
        ON profile.user_id=auth_user.id
        WHERE chat_id='{chat_id}'""")
    user_profile = cur.fetchone()
    cur.close()
    db.close()
    return user_profile


def get_delivery_settings(chat_id: int) -> tuple:
    """Получить настройки заказа"""
    db, cur = connect_db(f"""SELECT delivery, delivery_street, discount
    FROM profile 
    WHERE chat_id='{chat_id}'""")
    settings = cur.fetchone()
    cur.close()
    db.close()
    return settings


def get_delivery_shop(chat_id: int) -> tuple:
    """Получить магазин доставки"""
    db, cur = connect_db(f"""SELECT shops.name
        FROM profile 
        INNER JOIN shops 
        ON profile.main_shop_id = shops.id
        WHERE chat_id='{chat_id}'""")
    shop = cur.fetchone()[0]
    cur.close()
    db.close()
    return shop


def get_best_discount(chat_id: int = None) -> tuple:
    """Получить лучшую скидку"""
    db, cur = connect_db(f"""SELECT MIN(sale) FROM shops""")
    shop_discount = cur.fetchone()

    if chat_id:
        db, cur = connect_db(f"""SELECT discount
            FROM profile 
            WHERE chat_id='{chat_id}'""")
        user_discount = cur.fetchone()
        best_discount = min(user_discount, shop_discount)
    else:
        best_discount = shop_discount
    cur.close()
    db.close()

    return best_discount[0]


def get_user_phone(chat_id: int) -> None or str:
    """Получить магазин пользователя"""
    db, cur = connect_db(f"SELECT phone FROM profile WHERE chat_id='{chat_id}'")
    phone = cur.fetchone()[0]
    cur.close()
    db.close()
    return phone


def get_user_address(chat_id: int) -> None or str:
    """Получить адрес пользователя"""
    db, cur = connect_db(f"SELECT delivery_street FROM profile WHERE chat_id='{chat_id}'")
    street = cur.fetchone()[0]
    cur.close()
    db.close()
    return street


def get_user_shop(chat_id: int) -> None or str:
    """Получить магазин пользователя"""
    db, cur = connect_db(f"SELECT main_shop FROM profile WHERE chat_id='{chat_id}'")
    street = cur.fetchone()[0]
    cur.close()
    db.close()
    return street


def save_order(chat_id: int, delivery_info: str, cart_price: int, discount=1, payment_type: int = 2) -> list and int:
    """Сохранить заказ"""
    db, cur = connect_db(f"""SELECT carts.product_id, carts.amount FROM carts
    INNER JOIN profile ON profile.id = carts.profile_id
    WHERE profile.chat_id='{chat_id}' AND carts.order_id IS NULL""")
    products_id, products_amount = list(zip(*cur.fetchall()))

    cur.execute(f"""INSERT INTO orders (profile_id, delivery_info, order_price, deliver, discount, date, status_id, payment_id ,payed, payed_delivery, delivery_price, manager_message_id) 
    SELECT id, '{delivery_info}', '{cart_price}', profile.delivery, '{discount}','{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}','1' ,'{payment_type}' ,'0', '0', 0, 0
    FROM profile WHERE profile.chat_id='{chat_id}'""")
    db.commit()

    cur.execute(f"""SELECT MAX(orders.id), profile.id FROM orders 
    INNER JOIN profile ON profile.id = orders.profile_id
    WHERE profile.chat_id='{chat_id}'""")
    order_id, profile_id = cur.fetchall()[0]

    cur.execute(f"""UPDATE carts SET order_id = '{order_id}'
    WHERE profile_id = '{profile_id}' AND order_id IS NULL AND soft_delete='0'""")
    db.commit()
    cur.close()
    db.close()
    products_names = _id_to_name('products', products_id)
    products = zip(products_names, products_amount)
    return products, order_id


def add_manager_message_id(order_id: int, message_id: int):
    """Добавить номер сообщения в канале менеджеров в заказ"""
    db, cur = connect_db(f"""UPDATE orders 
        SET orders.manager_message_id = '{message_id}'
        WHERE orders.id = '{order_id}'""")
    db.commit()
    cur.close()
    db.close()


def get_user_orders(chat_id: int, filter: str = '') -> list:
    """Получить список заказов пользователя"""
    db, cur = connect_db(f"""SELECT orders.id, products.name, products.price ,carts.amount, orders.order_price, order_status.title, orders.payment_url, orders.extra_payment_url, orders.tracing_num, products.sale, orders.discount, delivery_price
    FROM orders
    INNER JOIN carts ON orders.id = carts.order_id 
    INNER JOIN products ON carts.product_id = products.id
    INNER JOIN profile ON profile.id = orders.profile_id
    INNER JOIN order_status ON orders.status_id = order_status.id
    WHERE profile.chat_id='{chat_id}' {filter}
    ORDER BY orders.id""")
    orders = cur.fetchall()
    cur.close()
    db.close()
    return orders


def get_order_address(order_id: int) -> None or str:
    """Получить адрес заказа"""
    db, cur = connect_db(f"SELECT delivery_info FROM orders WHERE id='{order_id}'")
    address = cur.fetchone()[0]
    cur.close()
    db.close()
    return address


def count_user_messages(chat_id: int):
    """ Сохранить сообщение от пользователя """
    db, cur = connect_db(f"""SELECT count(user_message.id) 
    FROM user_message 
    INNER JOIN profile 
    ON profile.id = user_message.user_id
    WHERE profile.chat_id='{chat_id}' and user_message.checked='0'""")
    messages = cur.fetchone()
    cur.close()
    db.close()
    return messages[0]


def save_user_message(chat_id: int, message: str):
    """ Сохранить сообщение от пользователя """
    try:
        db, cur = connect_db(f"""INSERT INTO user_message (date, user_id, manager_id, message, checked) 
        SELECT '{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', id, NULL, '{message}', '0'
        FROM profile WHERE profile.chat_id='{chat_id}'""")
        db.commit()
        cur.close()
        db.close()
    except Exception:
        return f'К сожалению произошла ошибка попробуйте отправить сообщение еще раз или обратитесь в поддержку {ADMIN_TG}'
    return 'Мы получили ваше сообщение.В ближайшее время менеджер c вами свяжется...'


""" Административные """


def get_waiting_payment_orders() -> list:
    """Возврачает список заявок ожидающих оплаты"""
    db, cur = connect_db(f"""SELECT orders.id, profile.chat_id, orders.order_price, orders.discount, orders.deliver, orders.delivery_price, orders.payment_url, orders.extra_payment_url
        FROM orders
        INNER JOIN profile ON profile.id = orders.profile_id
        WHERE orders.status_id='2'""")
    request = cur.fetchall()
    cur.close()
    db.close()
    return request


def save_payment_link(order_id: int, link: str, field):
    db, cur = connect_db(f"""UPDATE orders SET {field}='{link}' WHERE id='{order_id}'""")
    db.commit()
    cur.close()
    db.close()


def order_payed(set_str: str, order_id: int):
    """Помечает ордер оплаченым"""
    db, cur = connect_db(
        f"""UPDATE orders SET {set_str}
        WHERE id='{order_id}'""")
    db.commit()
    cur.close()
    db.close()
