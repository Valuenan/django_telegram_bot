from shop.telegram.banking import avangard_check
from shop.telegram.bot import ready_order_message, send_message_to_user
from shop.telegram.db_connection import get_waiting_payment_orders, order_payed


def check_orders_payment(session=None):
    status = ''
    orders_for_check = get_waiting_payment_orders()
    if orders_for_check:
        for order in orders_for_check:

            order_id, user, price = order
            if session:
                status, session = avangard_check(customer=user, order_num=order_id, order_sum=int(price),
                                                 session=session)
            else:
                status, session = avangard_check(customer=user, order_num=order_id, order_sum=int(price))
            if status.strip() == "Оплата поступила":
                order_payed(order_id)
                ready_order_message(chat_id=user, order_id=order_id, status='2')

    return session
