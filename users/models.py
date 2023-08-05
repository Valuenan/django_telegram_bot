import decimal

from django.contrib.auth.models import User
from django.db import models

from shop.models import Product, Shop

ORDER_STATUS = (
    ('0', 'Заявка обрабатывается 📝'),
    ('1', 'Сборка заказа 📦'),
    ('2', 'Доставка 🚚'),
    ('3', 'Ожидает в пункте выдачи 🚶‍♂️'),
    ('4', 'Получен ✅'),
    ('5', 'Отменен ❌')
)
PAYMENT = (
    ('0', '🎟️ Наличными'),
    ('1', '💳 Безналично'),
    ('2', '📱 Перевод'),
)


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name='Пользователь')
    phone = models.CharField(verbose_name='Номер телефона', max_length=12, blank=True, null=True)
    chat_id = models.BigIntegerField(verbose_name='ИД чата пользователя', db_index=True, unique=True)
    cart_message_id = models.IntegerField(verbose_name='ИД сообщения корзины', blank=True, null=True)
    discount = models.SmallIntegerField(verbose_name='Скидка', default=0)
    delivery = models.BooleanField(verbose_name='Доставка', default=False)
    main_shop = models.ForeignKey(Shop, on_delete=models.DO_NOTHING, verbose_name='Магазин доставки', null=True,
                                  blank=True)
    delivery_street = models.CharField(max_length=200, verbose_name='Улица доставки', blank=True, null=True)

    def __str__(self):
        return f'{self.user} - номер чата {self.chat_id} - работник {self.user.is_staff}'

    class Meta:
        db_table = 'profile'
        verbose_name = 'Профиль'
        verbose_name_plural = 'Профили'


class OrderStatus(models.Model):
    title = models.CharField(max_length=50, verbose_name='Статус заказа', choices=ORDER_STATUS, blank=False,
                             default='Заявка обрабатывается 📝')

    def __str__(self):
        return self.get_title_display()

    class Meta:
        db_table = 'order_status'
        verbose_name = 'Статус заказа'
        verbose_name_plural = 'Статусы заказа'


class Payment(models.Model):
    title = models.CharField(max_length=50, verbose_name='Виды оплат', choices=PAYMENT, blank=False,
                             default='🎟️ Наличными')

    def __str__(self):
        return self.get_title_display()

    class Meta:
        db_table = 'order_payment'
        verbose_name = 'Вид оплаты'
        verbose_name_plural = 'Виды оплаты'


class Orders(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, verbose_name='Пользователь')
    date = models.DateField(auto_now_add=True, verbose_name='Дата заказа')
    delivery_info = models.CharField(max_length=500, verbose_name='Информация о доставке', null=True, blank=True)
    order_price = models.DecimalField(max_digits=7, decimal_places=2, verbose_name='Цена заказа')
    admin_check = models.CharField(max_length=100, verbose_name='Заявка принята работником:', null=True, blank=True)
    deliver = models.BooleanField(verbose_name='Доставить по адресу')
    status = models.ForeignKey(OrderStatus, blank=True, on_delete=models.DO_NOTHING, verbose_name='Статус заказа')
    payment = models.ForeignKey(Payment, blank=True, null=True, on_delete=models.DO_NOTHING, verbose_name='Вид оплаты')

    def __str__(self):
        return f'Заказ номер: {self.id} , статус {self.status} - {self.profile.user.username} - сумма {self.order_price} - подтвердил {self.admin_check}'

    def update_order_sum(self, order_carts):
        order_sum = 0
        for item in order_carts:
            item.price = item.product.price
            order_sum += item.amount * item.price
        return order_sum

    def update_order_quantity(self, form: dict, rests_action: str, shop: int):
        """Обновляет количество товара и спысываем со склада"""
        """Приимаем на вход словарь где ключ - ид товара, значение - количество"""
        order_carts = self.carts_set.all()

        if rests_action == 'add' and not form:
            for item in order_carts.values():
                form[item['id']] = item['amount']

        for cart_id in form:
            cart_item = order_carts.filter(id=cart_id)[0]
            if cart_item:
                amount = decimal.Decimal(form[cart_id])
                if amount > decimal.Decimal(0):
                    cart_item.soft_delete = False
                    cart_item.product.edit_rests(rests_action, shop, cart_item.amount, amount)
                    cart_item.amount = amount
                    cart_item.save()
                elif amount <= decimal.Decimal(0):
                    cart_item.amount = 0
                    cart_item.soft_delete = True
                    cart_item.save()

        self.order_price = self.update_order_sum(order_carts)
        self.save()

    def update_order_status(self, new_status: str):
        """Обновляет статус возвращаем действие для склада"""
        rests_action = 'pass'
        if self.status.title != new_status:
            if new_status == "0":
                rests_action = 'add'
            elif self.status.title == "0":
                rests_action = 'remove'
            self.status = OrderStatus.objects.filter(title=new_status)[0]
            self.save()
        return rests_action

    class Meta:
        db_table = 'orders'
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'


class Carts(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, verbose_name='Пользователь')
    product = models.ForeignKey(Product, on_delete=models.DO_NOTHING, verbose_name='Товары')
    amount = models.DecimalField(max_digits=6, decimal_places=3, verbose_name='Количество', default=0)
    price = models.DecimalField(max_digits=7, decimal_places=2, verbose_name='Цена')
    order = models.ForeignKey(Orders, on_delete=models.DO_NOTHING, verbose_name='Заказ', blank=True, null=True)
    soft_delete = models.BooleanField(verbose_name='Удалить', default=False)

    def __str__(self):
        return f'{self.profile.user.username} - товар {self.product} - работник {self.amount} - цена {self.product}'

    class Meta:
        db_table = 'carts'
        verbose_name = 'Корзина'
        verbose_name_plural = 'Корзины'
