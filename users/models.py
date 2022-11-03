from django.contrib.auth.models import User
from django.db import models

from shop.models import Product


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name='Пользователь')
    chat_id = models.IntegerField(verbose_name='ИД чата пользователя', db_index=True, unique=True)
    cart_message_id = models.IntegerField(verbose_name='ИД сообщения корзины', blank=True, null=True)
    discount = models.SmallIntegerField(verbose_name='Скидка', default=0)
    delivery = models.BooleanField(verbose_name='Доставка', default=False)
    main_shop = models.CharField(max_length=50, verbose_name='Магазин доставки', null=True, blank=True)
    payment_cash = models.BooleanField(verbose_name='Оплачивать наличными', default=True)
    delivery_street = models.CharField(max_length=200, verbose_name='Улица доставки', blank=True, null=True)

    def __str__(self):
        return f'{self.user} - номер чата {self.chat_id} - работник {self.user.is_staff}'

    class Meta:
        db_table = 'profile'
        verbose_name = 'Профиль'
        verbose_name_plural = 'Профили'


class Carts(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, verbose_name='Пользователь')
    product = models.ForeignKey(Product, on_delete=models.DO_NOTHING, verbose_name='Товары')
    amount = models.SmallIntegerField(verbose_name='Количество')
    price = models.IntegerField(verbose_name='Цена')

    def __str__(self):
        return f'{self.profile.user.name} - товар {self.product} - работник {self.amount} - цена {self.product}'

    class Meta:
        db_table = 'carts'
        verbose_name = 'Корзина'
        verbose_name_plural = 'Корзины'


class Orders(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, verbose_name='Пользователь')
    product = models.ManyToManyField(Product, verbose_name='Товар')
    delivery_info = models.CharField(max_length=500, verbose_name='Информация о доставке')
    order_price = models.IntegerField(verbose_name='Цена заказа')
    soft_delete = models.BooleanField(verbose_name='Удалить', default=False)
    admin_check = models.CharField(max_length=100, verbose_name='Заявка принята работником:', null=True, blank=True)

    def __str__(self):
        return f'Заказ номер: {self.id} - {self.profile.user.name} - сумма {self.order_price} - подтвердил {self.admin_check}, пометка удаления {self.soft_delete}'

    class Meta:
        db_table = 'orders'
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'
