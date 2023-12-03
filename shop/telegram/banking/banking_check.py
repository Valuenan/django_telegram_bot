from decimal import Decimal

from shop.telegram.banking.banking import avangard_check
from shop.telegram.bot import ready_order_message, message_to_manager
from users.models import Orders, OrderStatus


def check_orders_payment():
    orders_for_check = Orders.objects.filter(status=2)
    if orders_for_check:
        checked_orders = avangard_check(orders=orders_for_check)

        for order, payed in checked_orders.items():
            if order:
                order_sum = 0
                order = order[0]
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
                user = int(order.profile)
                if order.payment_url and order.extra_payment_url is None:
                    if payed == order_sum:
                        if order.deliver:
                            order.payed, order.status = True, OrderStatus.objects.filter(id=3)[0]
                            order.save()
                            ready_order_message(chat_id=user, order_id=order.id, status='2', deliver=order.deliver,
                                                order_sum=order_sum, bot_action=True)
                        else:
                            order.payed, order.status = True, OrderStatus.objects.filter(id=5)[0]
                            order.save()
                            ready_order_message(chat_id=user, order_id=order.id, status='4', deliver=order.deliver,
                                                order_sum=order_sum, bot_action=True)
                    elif order.delivery_price != 0 and payed == order_sum + order.delivery_price:
                        order.payed, order.payed_delivery, order.status = True, True, OrderStatus.objects.filter(id=4)[
                            0]
                        order.save()
                        ready_order_message(chat_id=user, order_id=order.id, status='3', deliver=order.deliver,
                                            order_sum=order_sum + order.delivery_price, tracing_num=order.tracing_num,
                                            bot_action=True)
                        message_to_manager(f'Поступила оплата по заказу № {order.id}')
                    else:
                        message_to_manager(f'ОШИБКА. Бот не смог распределить оплату заказа № {order.id}')
                else:
                    if payed == order.delivery_price:
                        order.payed, order.payed_delivery, order.status = True, True, OrderStatus.objects.filter(id=4)[
                            0]
                        order.save()
                        ready_order_message(chat_id=user, order_id=order.id, status='3', deliver=order.deliver,
                                            order_sum=order_sum + order.delivery_price, tracing_num=order.tracing_num,
                                            bot_action=True)
                        message_to_manager(f'Поступила оплата за доставку по заказу № {order.id}')
                    else:
                        message_to_manager(f'ОШИБКА. Бот не смог распределить оплату заказа № {order.id}')
