from django import template

from shop.models import Shop

register = template.Library()


@register.simple_tag()
def get_shops():
    '''Вывод названия магазинов'''
    return {'shops': Shop.objects.all()}

@register.simple_tag()
def get_sum(amount, price):
    '''Вывод сумму стоимости товара'''
    return amount * price
