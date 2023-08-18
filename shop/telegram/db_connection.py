from datetime import datetime

import mysql.connector
from mysql.connector import Error

from django_telegram_bot.settings import DATABASES

ADMIN_TG = '@Vassagio'
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

            text = f'''В данный момент бот работает в тестовом режиме, при возникновении проблем обращайтесть к администратору {ADMIN_TG}
            
Добро пожаловать {first_name}, для оформления заказов нужно указать номер телефона. Отправьте в чат номер телефона.'''
            error = 'no-phone'
        except Exception as err:
            text = f'''Извините {first_name} произошла ошибка, попробуйте еще раз нажать -> /start <-.
Если ошибка повторяется, обратитесь к администратору {ADMIN_TG}'''
            error = err
    elif user_phone is None:
        text = f'''Добро пожаловать {first_name}, нужно указать номер телефона. Отправьте в чат номер телефона. (формат +7*** или 8***)'''
        error = 'no-phone'
    else:
        text, error = f'Добро пожаловать {first_name}.', 'ok'
    return text, error


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
        self_category_name = cur.fetchone()
        cur.close()
        db.close()
        return categories, self_category_name
    else:
        db, cur = connect_db("SELECT command, id, parent_category_id FROM categories WHERE parent_category_id is NULL")
        categories = cur.fetchall()
        cur.close()
        db.close()
        return categories


def get_products(chosen_category: int, page: int) -> (list, int):
    """Получить список товаров и пагинация"""
    db, cur = connect_db((f"""
    SELECT products.id, products.name, products.img, products.price, products.category_id, sum(rests.amount) AS rest
    FROM products 
    INNER JOIN rests ON products.id = rests.product_id
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
        if command == 'add' or command == 'add-cart':
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
    return amount, product


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
    db, cur = connect_db(f"""SELECT products.name, carts.amount, carts.price 
    FROM carts  
    INNER JOIN products 
    ON carts.product_id = products.id 
    WHERE carts.order_id IS NULL AND carts.profile_id = (SELECT id FROM profile where chat_id='{chat_id}')""")
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


def load_last_order() -> int:
    """Получить номер последнего заказа"""
    db, cur = connect_db(f"""SELECT MAX(id) FROM orders""")
    prev_order = cur.fetchone()[0]
    cur.close()
    db.close()
    if prev_order is None:
        prev_order = 0
    return prev_order + 1


def save_delivery_settings(value: bool or str, field: str, chat_id: int):
    """Сохранить настроки заказа"""
    db, cur = connect_db(f"UPDATE profile SET {field}='{value}' WHERE chat_id='{chat_id}'")
    db.commit()
    cur.close()
    db.close()


def get_delivery_settings(chat_id: int) -> tuple:
    """Получить настройки заказа"""
    db, cur = connect_db(f"""SELECT profile.delivery, profile.delivery_street
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


def save_order(chat_id: int, delivery_info: str, cart_price: int) -> list and int:
    """Сохранить заказ"""
    db, cur = connect_db(f"""SELECT profile.id FROM profile
    WHERE profile.chat_id='{chat_id}'""")
    profile_id = cur.fetchone()[0]

    db, cur = connect_db(f"""SELECT carts.product_id, carts.amount FROM carts
    WHERE carts.profile_id={profile_id} AND carts.order_id IS NULL""")
    products_id, products_amount = list(zip(*cur.fetchall()))

    db, cur = connect_db(f"""INSERT INTO orders (profile_id, delivery_info, order_price, deliver, date, status_id, payed, delivery_price) 
    SELECT id, '{delivery_info}', '{cart_price}', delivery, '{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', '1', '0', 0
    FROM profile WHERE profile.chat_id='{chat_id}'""")
    db.commit()

    cur.execute(f"""UPDATE carts
    SET order_id = (SELECT MAX(orders.id) FROM orders 
    WHERE orders.profile_id='{profile_id}' AND soft_delete='0')
    WHERE carts.profile_id='{profile_id}' AND carts.order_id IS NULL""")
    db.commit()
    cur.close()
    db.close()
    products_names = _id_to_name('products', products_id)
    products = zip(products_names, products_amount)
    return products, cart_price


def get_user_orders(chat_id: int, filter: str = '') -> list:
    """Получить список заказов пользователя"""
    db, cur = connect_db(f"""SELECT orders.id, products.name, products.price ,carts.amount, orders.order_price, order_status.title
    FROM orders
    INNER JOIN carts ON orders.id = carts.order_id 
    INNER JOIN products ON carts.product_id = products.id
    INNER JOIN profile ON profile.id = orders.profile_id
    INNER JOIN order_status ON orders.status_id = order_status.id
    WHERE profile.chat_id='{chat_id}' {filter}""")
    orders = cur.fetchall()
    cur.close()
    db.close()
    return orders


""" Административные """


def get_waiting_orders() -> list:
    """Возврачает список заявок ожидающих отгрузки"""
    db, cur = connect_db(f"""SELECT orders.id, auth_user.username, orders.order_price, orders.status_id 
    FROM orders
    INNER JOIN profile ON profile.id = orders.profile_id
    INNER JOIN auth_user ON profile.user_id = auth_user.id
    WHERE orders.status_id='2' OR orders.status_id='3'""")
    request = cur.fetchall()
    cur.close()
    db.close()
    return request


def save_payment_link(order_id: int, link: str):
    db, cur = connect_db(f"""UPDATE orders SET payment_url='{link}' WHERE id='{order_id}'""")
    db.commit()
    cur.close()
    db.close()


def order_payed(chat_id: int, order_sum: int):
    """Помечает ордер оплаченым"""
    db, cur = connect_db(f"""SELECT profile.id FROM profile
        WHERE profile.chat_id='{chat_id}'""")
    profile_id = cur.fetchone()[0]
    db, cur = connect_db(
        f"""UPDATE orders SET payed='1', status_id='3' 
        WHERE profile_id='{profile_id}' AND order_price + delivery_price='{order_sum}'""")
    db.commit()
    cur.close()
    db.close()
