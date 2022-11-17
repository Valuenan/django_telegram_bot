import sqlite3
import xlrd
from django_telegram_bot.settings import BASE_DIR

BD = BASE_DIR / 'db.sqlite3'
PRODUCTS_PAGINATION_NUM = 5


def connect_db():
    db = sqlite3.connect(BD)
    cur = db.cursor()
    return db, cur


def _id_to_name(table: str, ids: list) -> list:
    names = []
    db, cur = connect_db()
    for item_id in ids:
        names.append(cur.execute(f"SELECT name FROM {table} WHERE id='{item_id[0]}'").fetchone()[0])
    db.close()
    return names


def check_user_is_staff(username: str) -> (str or None):
    db, cur = connect_db()
    admin = cur.execute(f"SELECT is_staff FROM auth_user WHERE username='{username}'").fetchone()
    db.close()
    return admin


def start_user(first_name: str, last_name: str, username: str, chat_id: int, cart_message_id: (int or None),
               discount: int) -> (
        str, str):
    """Запись новых пользователей"""
    db, cur = connect_db()
    user_id = cur.execute(f"SELECT id FROM auth_user WHERE username='{username}'").fetchone()
    if user_id is None:
        try:
            cur.execute(f"""INSERT INTO auth_user (first_name, last_name, username, is_staff, is_superuser, is_active, email, password, date_joined) 
            VALUES ('{first_name}', '{last_name}', '{username}','{False}', '{False}','{True}', 'user@email.ru' ,'UserPassword333', CURRENT_TIMESTAMP)""")
            db.commit()

            user_id = cur.execute(f"SELECT id FROM auth_user WHERE username='{username}'").fetchone()

            cur.execute(f"""INSERT INTO profile (user_id, chat_id, cart_message_id, discount, delivery, payment_cash) 
            VALUES ('{user_id[0]}', {chat_id}, '{cart_message_id}', '{discount}', '{False}', '{False}')""")
            db.commit()
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


def get_category(category_id: int = None) -> list:
    """Получить список категорй"""
    if category_id is not None:
        db, cur = connect_db()
        category = cur.execute(f"SELECT * FROM categories WHERE id='{category_id}'").fetchone()
        db.close()
        return list(category)
    else:
        db, cur = connect_db()
        categories = cur.execute("SELECT * FROM categories").fetchall()
        db.close()
        return categories


def get_products(command_filter: str, page: int) -> (list, int):
    """Получить список товаров и пагинация"""
    db, cur = connect_db()
    products = cur.execute(f"SELECT * FROM products WHERE category_id='{command_filter}'").fetchall()
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
    db, cur = connect_db()
    request = cur.execute(f"SELECT id FROM products WHERE name='{product_name}'").fetchone()[0]
    db.close()
    return request


def edit_to_cart(command: str, chat_id: int, product_id: int) -> (int, str):
    """Добавить/Удалить товар из корзины"""
    db, cur = connect_db()
    profile_id = cur.execute(f"SELECT id FROM profile WHERE chat_id='{chat_id}'").fetchone()[0]
    product_info = cur.execute(
        f"SELECT amount FROM carts WHERE profile_id='{profile_id}' and product_id='{product_id}'").fetchone()
    if product_info is None and command == 'add' or product_info is None and command == 'add-cart':
        product_price = cur.execute(f"SELECT price FROM products WHERE id='{product_id}'").fetchone()[0]
        data = [profile_id, product_id, 1, product_price]
        cur.execute(f"INSERT INTO carts (profile_id, product_id, amount, price) VALUES (?, ?, ?, ?)", data)
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
            cur.execute(f"DELETE FROM carts WHERE profile_id='{profile_id}' and product_id='{product_id}'")
        else:
            cur.execute(
                f"UPDATE carts SET amount='{amount}' WHERE profile_id='{profile_id}' and product_id='{product_id}'")
    db.commit()
    product = cur.execute(f"SELECT name FROM products WHERE id='{product_id}'").fetchone()[0]
    db.close()
    return amount, product


def old_cart_message_to_none(chat_id: int):
    """Id открытой корзины переставить в None"""
    db, cur = connect_db()
    cur.execute(f"UPDATE profile SET cart_message_id='{None}' WHERE chat_id='{chat_id}'")
    db.commit()
    db.close()


def old_cart_message(chat_id) -> (int or None):
    """Получение id сообщения корзины в базе наличия открытой корзины"""
    db, cur = connect_db()
    cart_message_id = cur.execute(f"SELECT cart_message_id FROM profile WHERE chat_id='{chat_id}'").fetchone()
    db.commit()
    db.close()
    if cart_message_id is None:
        return cart_message_id
    else:
        return cart_message_id[0]


def show_cart(chat_id: int) -> list:
    """Получить список товаров в корзине"""
    db, cur = connect_db()
    profile_id = cur.execute(f"SELECT id FROM profile WHERE chat_id='{chat_id}'").fetchone()[0]
    cart_info = cur.execute(f"""SELECT products.name, carts.amount, carts.price 
    FROM carts  
    INNER JOIN products 
    ON carts.product_id = products.id 
    WHERE profile_id='{profile_id}'""").fetchall()
    if cart_info is None:
        cart_list = []
    else:
        cart_list = cart_info
    db.close()
    return cart_list


def save_cart_message_id(chat_id: int, cart_message_id: int):
    """Сохраняет id сообщения с корзиной"""
    db, cur = connect_db()
    cur.execute(f"UPDATE profile SET cart_message_id='{cart_message_id}' WHERE chat_id='{chat_id}'")
    db.commit()
    db.close()


def db_delete_cart(chat_id: int):
    """Удалить корзину"""
    db, cur = connect_db()
    profile_id = cur.execute(f"SELECT id FROM profile WHERE chat_id='{chat_id}'").fetchone()[0]
    cur.execute(f"DELETE FROM carts WHERE profile_id='{profile_id}'")
    cur.execute(f"UPDATE profile SET cart_message_id='{None}' WHERE chat_id='{chat_id}'")
    db.commit()
    db.close()


def load_last_order(db, cur) -> int:
    """Получить номер последнего заказа"""
    prev_order = cur.execute('SELECT MAX(id) FROM orders').fetchone()[0]
    db.close()
    if prev_order is None:
        prev_order = 0
    return prev_order + 1


def save_delivery_settings(value: bool or str, field: str, chat_id: int):
    """Сохранить настроки заказа"""
    db, cur = connect_db()
    cur.execute(f"UPDATE profile SET {field}='{value}' WHERE chat_id='{chat_id}'")
    db.commit()
    db.close()


def check_products_in_shop(user: str, shop: str):
    """Сохранить настроки заказа"""
    db, cur = connect_db()
    user_products = {}
    user_cart = cur.execute(f"SELECT product, amount FROM carts WHERE user='{user}'").fetchall()
    for product in user_cart:
        dict(product)
    shop_products = cur.execute(
        f"SELECT name, rests_prachecniy, rests_kievskaya FROM products WHERE name IN {user_products}").fetchall()
    db.close()


def get_delivery_settings(chat_id: int) -> tuple:
    """Получить настройки заказа"""
    db, cur = connect_db()
    settings = cur.execute(f"SELECT * FROM profile WHERE chat_id='{chat_id}'").fetchone()
    db.close()
    return settings


def get_user_address(chat_id: int) -> None or str:
    db, cur = connect_db()
    street = cur.execute(f"SELECT delivery_street FROM profile WHERE chat_id='{chat_id}'").fetchone()[0]
    db.close()
    return street


def save_order(chat_id: int, delivery_info: str, cart_price: int) -> list and int:
    """Сохранить заказ"""
    db, cur = connect_db()
    profile_id = cur.execute(f"SELECT id FROM profile WHERE chat_id='{chat_id}'").fetchone()[0]
    products_id = cur.execute(f"SELECT product_id FROM carts WHERE profile_id='{profile_id}'").fetchall()
    cur.execute(f"""INSERT INTO orders (profile_id, delivery_info, order_price, soft_delete) 
    VALUES ('{profile_id}', '{delivery_info}', '{cart_price}', 'False')""")
    db.commit()
    order_id = \
        cur.execute(f"SELECT max(id) FROM orders WHERE profile_id='{profile_id}' AND soft_delete='False'").fetchone()[0]
    for product_id in products_id:
        cur.execute(f"""INSERT INTO orders_product (orders_id, product_id) 
            VALUES ('{order_id}', '{product_id[0]}')""")
    db.commit()
    db.close()
    db_delete_cart(chat_id)
    products_names = _id_to_name('products', products_id)
    return products_names, cart_price


def get_user_orders(chat_id: int) -> list:
    """Получить список заказов пользователя"""
    db, cur = connect_db()
    profile_id = cur.execute(f"SELECT id FROM profile WHERE chat_id='{chat_id}'").fetchone()[0]
    orders = cur.execute(f"""SELECT orders.id, orders.order_price, products.name 
    FROM orders 
    INNER JOIN orders_product ON orders.id = orders_product.orders_id 
    INNER JOIN products ON orders_product.product_id = products.id
    WHERE profile_id='{profile_id}'""").fetchall()
    db.close()
    return orders


""" Административные """


def get_waiting_orders() -> list:
    """Возврачает список заявок ожидающих отгрузки"""
    db, cur = connect_db()
    request = cur.execute(f"SELECT id, user, order_price FROM orders WHERE soft_delete='False'").fetchall()
    db.close()
    return request


def get_user_id_chat(customer: str) -> int:
    """Возвращает ид чата по логину"""
    db, cur = connect_db()
    request = cur.execute(f"SELECT chat_id FROM users WHERE username='{customer}'").fetchone()[0]
    db.close()
    return request


def soft_delete_confirmed_order(order_id: int, admin_username: str):
    """Помечает удаленными выполненые ордера и ник администратора отметившего"""
    db, cur = connect_db()
    request = cur.execute(f"UPDATE orders SET soft_delete='True', admin_check='{admin_username}' WHERE id='{order_id}'")
    db.commit()
    db.close()
    return request

# if __name__ == '__main__':
#     """Загружаем данные из exel, если нет базы то создать"""
#     try:
#         db_create()
#     except sqlite3.OperationalError:
#         load_data_from_exel()
