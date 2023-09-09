from django import template
from django.template.defaultfilters import floatformat

from shop.models import Shop

register = template.Library()


@register.simple_tag()
def get_shops():
    """Вывод названия магазинов"""
    return {'shops': Shop.objects.all()}


@register.simple_tag()
def get_sum(amount, price):
    """Вывод сумму стоимости товара"""
    return round(amount * price, 2)


@register.simple_tag()
def get_full_price(price, discount, delivery):
    """Стоимость с доставкой"""
    return round(round(price * discount + delivery), 2)


@register.simple_tag()
def get_discount(decimal_discount):
    """Расчет скидки"""
    return int(100 - decimal_discount * 100)


@register.simple_tag()
def formatted_float(value):
    value = floatformat(value, arg=3)
    return str(value).replace(',', '.')
