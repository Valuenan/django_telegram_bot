import psycopg2
from psycopg2.extras import DictCursor

from django_telegram_bot.settings import DATABASES

PRODUCTS_PAGINATION_NUM = 5
DATABASE = DATABASES['default']['NAME']
HOST = DATABASES['default']['HOST']
DB_USER = DATABASES['default']['USER']
BD_PASSWORD = DATABASES['default']['PASSWORD']
BD_PORT = DATABASES['default']['PORT']


def connect_db(sql_request: str) -> object:
    db = psycopg2.connect(database=DATABASE,
                          host=HOST,
                          user=DB_USER,
                          password=BD_PASSWORD,
                          port=BD_PORT)
    cur = db.cursor(cursor_factory=DictCursor)
    cur.execute(sql_request)
    return db, cur


def _id_to_name(table: str, ids: list) -> list:
    names = []

    for item_id in ids:
        db, cur = connect_db(f"SELECT name FROM {table} WHERE id='{item_id[0]}'")
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
    db, cur = connect_db(f"SELECT id FROM auth_user WHERE username='{username}'")
    user_id = cur.fetchone()
    cur.close()
    db.close()

    if user_id is None:
        try:
            db, cur = connect_db(f"""INSERT INTO auth_user (first_name, last_name, username, is_staff, is_superuser, is_active, email, password, date_joined) 
            VALUES ('{first_name}', '{last_name}', '{username}','{False}', '{False}','{True}', 'user@email.ru' ,'UserPassword333', CURRENT_TIMESTAMP)""")
            db.commit()

            db, cur = connect_db(f"""INSERT INTO profile (user_id, chat_id, cart_message_id, discount, delivery, payment_cash) 
            SELECT auth_user.id, {chat_id}, {cart_message_id}, '{discount}', '{False}', '{False}'
            FROM auth_user WHERE auth_user.username = '{username}'""")
            db.commit()
            cur.close()
            db.close()

            text = f'Добро пожаловать {first_name}'
            error = 'ok'
        except Exception as err:
            text = f'''Извените {first_name} произошла ошибка, попробуйте еще раз нажать /start. 
Если ошибка повторяется, обратитесь к администратору @Vesselii'''
            error = err
        return text, error
    else:
        return f'Добро пожаловать {username}', 'ok'


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
        db, cur = connect_db(f"SELECT * FROM categories WHERE id='{category_id}'")
        category = cur.fetchall()
        cur.close()
        db.close()
        return category
    else:
        db, cur = connect_db("SELECT * FROM categories")
        categories = cur.fetchall()
        cur.close()
        db.close()
        return categories


def get_products(chosen_category: str, page: int) -> (list, int):
    """Получить список товаров и пагинация"""
    db, cur = connect_db((f"""
    SELECT products.id, products.name, products.img, products.price, products.category_id, sum(rests.amount) AS rest
    FROM products 
    INNER JOIN rests ON products.id = rests.product_id
    WHERE category_id='{chosen_category}'
    GROUP BY products.id
    ORDER BY products.id"""))
    products = cur.fetchall()
    cur.close()
    db.close()
    if len(products) > PRODUCTS_PAGINATION_NUM:
        count_pages = len(products) // PRODUCTS_PAGINATION_NUM
        start = page * PRODUCTS_PAGINATION_NUM
        end = start + PRODUCTS_PAGINATION_NUM
        return products[start: end], count_pages
    else:
        return products, None


def get_product_id(product_name: str) -> int:
    """Получить ид товара"""
    db, cur = connect_db(f"SELECT id FROM products WHERE name='{product_name}'")
    request = cur.fetchone()
    cur.close()
    db.close()
    return request


def edit_to_cart(command: str, chat_id: int, product_id: int) -> (int, str):
    """Добавить/Удалить товар из корзины"""
    db, cur = connect_db(f"""SELECT amount FROM carts 
    INNER JOIN profile ON profile.id = carts.profile_id
    WHERE profile.chat_id='{chat_id}' and carts.product_id='{product_id}'""")
    product_info = cur.fetchone()
    if product_info is None and command == 'add' or product_info is None and command == 'add-cart':
        db, cur = connect_db(f"SELECT price FROM products WHERE id='{product_id}'")
        product_price = cur.fetchone()[0]
        db, cur = connect_db(
            f"""INSERT INTO carts (profile_id, product_id, amount, price) 
            SELECT profile.id, '{product_id}', '1', '{product_price}' 
            FROM profile WHERE profile.chat_id='{chat_id}'""")
        amount = 1
    elif product_info is None and command == 'remove':
        amount = 0
    else:
        if command == 'add' or command == 'add-cart':
            amount = product_info[0] + 1
        elif command == 'remove' or command == 'remove-cart':
            amount = product_info[0] - 1
        else:
            amount = 0
        if amount == 0:
            db, cur = connect_db(f"""DELETE FROM carts
            WHERE carts.profile_id = (SELECT id FROM profile where chat_id='{chat_id}')
            AND carts.product_id='{product_id}'""")
        else:
            db, cur = connect_db(f"""UPDATE  carts SET amount='{amount}'
            WHERE carts.profile_id = (SELECT id FROM profile where chat_id='{chat_id}') 
            AND carts.product_id='{product_id}'""")
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
    WHERE carts.profile_id = (SELECT id FROM profile where chat_id='{chat_id}')""")
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
    db, cur = connect_db(f"DELETE FROM carts WHERE profile_id=(SELECT id FROM profile WHERE chat_id='{chat_id}')")
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


# def check_products_in_shop(user: str, shop: str):
#     """Проверка наличия товаров"""
#     db, cur = connect_db()
#     user_products = {}
#     user_cart = cur.execute(f"SELECT product, amount FROM carts WHERE user='{user}'").fetchall()
#     for product in user_cart:
#         dict(product)
#     shop_products = cur.execute(f"SELECT name, rests_prachecniy, rests_kievskaya FROM products WHERE name IN {user_products}").fetchall()
#     cur.close()
#     db.close()


def get_delivery_settings(chat_id: int) -> tuple:
    """Получить настройки заказа"""
    db, cur = connect_db(f"""SELECT delivery, main_shop_id, payment_cash, delivery_street
    FROM profile WHERE chat_id='{chat_id}'""")
    settings = cur.fetchone()
    cur.close()
    db.close()
    return settings


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
    db, cur = connect_db(f"""SELECT carts.product_id FROM carts
    INNER JOIN profile ON profile.id = carts.profile_id
    WHERE profile.chat_id='{chat_id}'""")
    products_id = cur.fetchall()
    db, cur = connect_db(f"""INSERT INTO orders (profile_id, delivery_info, order_price, soft_delete, deliver) 
    SELECT id, '{delivery_info}', '{cart_price}', 'False', delivery
    FROM profile WHERE profile.chat_id='{chat_id}'""")
    db.commit()
    for product_id in products_id:
        cur.execute(f"""INSERT INTO orders_product (orders_id, product_id) 
        SELECT max(orders.id), '{product_id[0]}' FROM orders 
        INNER JOIN profile ON profile.id = orders.profile_id
        WHERE profile.chat_id='{chat_id}' AND soft_delete='False'""")
    db.commit()
    cur.close()
    db.close()
    db_delete_cart(chat_id)
    products_names = _id_to_name('products', products_id)
    return products_names, cart_price


def get_user_orders(chat_id: int) -> list:
    """Получить список заказов пользователя"""
    db, cur = connect_db(f"""SELECT orders.id, orders.order_price, products.name 
    FROM orders 
    INNER JOIN orders_product ON orders.id = orders_product.orders_id 
    INNER JOIN products ON orders_product.product_id = products.id
    INNER JOIN profile ON profile.id = orders.profile_id
    WHERE profile.chat_id='{chat_id}'""")
    orders = cur.fetchall()
    cur.close()
    db.close()
    return orders


""" Административные """


def get_waiting_orders() -> list:
    """Возврачает список заявок ожидающих отгрузки"""
    db, cur = connect_db(f"""SELECT orders.id, auth_user.username, orders.order_price 
    FROM orders
    INNER JOIN profile ON profile.id = orders.profile_id
    INNER JOIN auth_user ON profile.user_id = auth_user.id
    WHERE soft_delete='False'""")
    request = cur.fetchall()
    cur.close()
    db.close()
    return request


def get_user_id_chat(customer: str) -> int:
    """Возвращает ид чата по логину"""
    db, cur = connect_db(f"""SELECT profile.chat_id FROM auth_user 
    INNER JOIN profile ON profile.user_id = auth_user.id
    WHERE auth_user.username='{customer}'""")
    request = cur.fetchone()[0]
    cur.close()
    db.close()
    return request


def soft_delete_confirmed_order(order_id: int, admin_username: str):
    """Помечает удаленными выполненые ордера и ник администратора отметившего"""
    db, cur = connect_db(f"UPDATE orders SET soft_delete='True', admin_check='{admin_username}' WHERE id='{order_id}'")
    db.commit()
    cur.close()
    db.close()
