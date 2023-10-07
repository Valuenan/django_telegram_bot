from time import sleep

from shop.telegram.banking.banking import avangard_check
from shop.telegram.bot import ready_order_message
from shop.telegram.db_connection import get_waiting_payment_orders, order_payed


def check_orders_payment():
    orders_for_check = get_waiting_payment_orders()
    orders_id = {}
    if orders_for_check:
        for order in orders_for_check:
            order_id, user, products_price, deliver, delivery_price, payment_url, extra_payment_url = order
            orders_id[str(order_id)] = [None, (
                order_id, user, products_price, deliver, delivery_price, payment_url, extra_payment_url)]

        checked_orders_id = avangard_check(orders_id=orders_id)

        for order_id_, data in checked_orders_id.items():
            if data[0]:
                payed = int(data[0].replace(' ', ''))
                order_id, user, products_price, deliver, delivery_price, payment_url, extra_payment_url = data[1]
                products_price = int(products_price)
                order_sum = products_price+delivery_price
                sleep(1)
                if payed and extra_payment_url is None:
                    if payed == products_price:
                        if deliver:
                            order_payed(set_str='payed="1", status_id="3"', order_id=order_id)
                            ready_order_message(chat_id=user, order_id=order_id, status='2', deliver=deliver, order_sum=order_sum, bot_action=True)
                        else:
                            order_payed(set_str='payed="1", status_id="5"', order_id=order_id)
                            ready_order_message(chat_id=user, order_id=order_id, status='4', deliver=deliver, order_sum=order_sum, bot_action=True)
                    elif delivery_price != 0 and payed == products_price + delivery_price:
                        order_payed(set_str='payed="1", payed_delivery="1", status_id="3"', order_id=order_id)
                        ready_order_message(chat_id=user, order_id=order_id, status='2', deliver=deliver, order_sum=order_sum, bot_action=True)
                else:
                    order_payed(set_str='payed_delivery="1", status_id="3"', order_id=order_id)
                    ready_order_message(chat_id=user, order_id=order_id, status='2', deliver=deliver, order_sum=order_sum, bot_action=True)
