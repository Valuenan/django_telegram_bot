from shop.telegram.banking import avangard_check
from shop.telegram.bot import ready_order_message
from shop.telegram.db_connection import get_waiting_payment_orders, order_payed


def check_orders_payment():
    orders_for_check = get_waiting_payment_orders()
    if orders_for_check:
        for order in orders_for_check:

            order_id, user, products_price, delivery_price, payment_url, extra_payment_url = order
            if extra_payment_url:
                payed_bool, payed_sum = avangard_check(payment_url=extra_payment_url)

                if payed_bool:
                    order_payed(set_str='payed_delivery="1"', order_id=order_id)
                    ready_order_message(chat_id=user, order_id=order_id, status='2')
            else:
                payed_bool, payed_sum = avangard_check(payment_url=payment_url)

                if payed_bool:
                    if payed_sum == products_price:
                        order_payed(set_str='payed="1"', order_id=order_id)
                        ready_order_message(chat_id=user, order_id=order_id, status='2')
                    elif delivery_price != 0 and payed_sum == products_price + delivery_price:
                        order_payed(set_str='payed="1", payed_delivery="1"', order_id=order_id)
                        ready_order_message(chat_id=user, order_id=order_id, status='2')