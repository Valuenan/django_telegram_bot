import decimal

from django.contrib.auth.models import User
from django.db import models

from shop.models import Product, Shop, SALE_TYPES

DISCUSSION_STATUS = (
    ('messaging', 'Принимаем сообщения пользователя'),
    ('phone_main', 'Запросить телефон'),
    ('phone', 'Запросить телефон из корзины'),
    ('phone_profile', 'Именить телефон в профиле'),
    ('first_name', 'Именить имя в профиле'),
    ('last_name', 'Именить фамилию в профиле'),
    ('address', 'Именить адрес магазина в профиле'),
    ('offer_address', 'Именить адрес доставки в профиле'),
)

ORDER_STATUS = (
    ('0', 'Заявка обрабатывается'),
    ('1', 'Ожидается оплата'),
    ('2', 'Сборка заказа'),
    ('3', 'Доставка'),
    ('4', 'Ожидает в пункте выдачи'),
    ('5', 'Получен'),
    ('6', 'Отменен'),
    ('7', 'Предзаказ')
)
PAYMENT = (
    ('0', 'Карта'),
    ('1', 'QR код'),
    ('2', 'Перевод'),
)

PREORDER_SELECTOR = (
    ('split', 'Разделить'),
    ('part-order', 'Только в наличии'),
    ('part-preorder', 'Только в предзаказ'),
    ('preorder', 'Все в предзаказ')
)


class Profile(models.Model):
    date = models.DateTimeField(verbose_name='Дата регистрации', auto_now_add=True)
    discussion_status = models.CharField(max_length=50, verbose_name='Ожидаемое действие от пользователя',
                                         choices=DISCUSSION_STATUS, default='messaging')
    telegram_name = models.CharField(verbose_name='Ник пользователя в Телеграм', max_length=50, blank=True, null=True)
    first_name = models.CharField(verbose_name='Имя пользователя', max_length=150, blank=True, null=True)
    last_name = models.CharField(verbose_name='Фамилия пользователя', max_length=150, blank=True, null=True)
    phone = models.CharField(verbose_name='Номер телефона', max_length=20, blank=True, null=True)
    chat_id = models.BigIntegerField(verbose_name='ИД чата пользователя', db_index=True, unique=True)
    cart_message_id = models.IntegerField(verbose_name='ИД сообщения корзины', blank=True, null=True)
    discount = models.DecimalField(verbose_name='Коэффициент скидки', max_digits=3, decimal_places=2, default=1)
    delivery = models.BooleanField(verbose_name='Доставка', default=False)
    main_shop = models.ForeignKey(Shop, on_delete=models.DO_NOTHING, verbose_name='Магазин доставки', null=True,
                                  blank=True)
    delivery_street = models.CharField(max_length=200, verbose_name='Улица доставки', blank=True, null=True)
    preorder = models.BooleanField(verbose_name='Показывать товары для предзаказа', default=True)
    preorder_selector = models.CharField(max_length=50, verbose_name='Выбор пользовтеля по корзине с предзаказом',
                                         choices=PREORDER_SELECTOR, default='Разделить')
    track = models.ManyToManyField(Product, verbose_name='Отсеживаемые товары', blank=True)

    def __str__(self):
        return f'{self.chat_id}'

    def __int__(self):
        return self.chat_id

    class Meta:
        db_table = 'profile'
        verbose_name = 'Профиль'
        verbose_name_plural = 'Профили'


class UserMessage(models.Model):
    date = models.DateTimeField(verbose_name='Дата, время сообщениея', auto_now_add=True)
    user = models.ForeignKey(Profile, on_delete=models.PROTECT, verbose_name='Пользователь')
    manager = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name='Менеждер', blank=True, null=True)
    message = models.CharField(max_length=500, verbose_name='Сообщение')
    checked = models.BooleanField(verbose_name='Прочитано', default=False)
    support_message_id = models.IntegerField(verbose_name='Номер сообщения в канале поддержки', blank=True, null=True)
    manager_signature = models.CharField(max_length=100, verbose_name='Подпись менеджера',
                                         blank=True, null=True)

    def __str__(self):
        return self.user.__str__()

    class Meta:
        db_table = 'user_message'
        verbose_name = 'Сообщение'
        verbose_name_plural = 'Сообщения'


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


class Carts(models.Model):
    date = models.DateTimeField(verbose_name='Дата, время сообщениея', auto_now_add=True)
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, verbose_name='Пользователь')
    product = models.ForeignKey(Product, on_delete=models.DO_NOTHING, verbose_name='Товары')
    amount = models.DecimalField(max_digits=6, decimal_places=3, verbose_name='Количество', default=0)
    price = models.DecimalField(max_digits=7, decimal_places=2, verbose_name='Цена')
    order = models.ForeignKey('Orders', on_delete=models.DO_NOTHING, verbose_name='Заказ', blank=True, null=True)
    preorder = models.BooleanField(verbose_name='Предзаказ', default=False)
    soft_delete = models.BooleanField(verbose_name='Удалить', default=False)

    def __str__(self):
        return self.profile.telegram_name

    class Meta:
        db_table = 'carts'
        verbose_name = 'Корзина'
        verbose_name_plural = 'Корзины'


class Orders(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, verbose_name='Пользователь')
    date = models.DateField(auto_now_add=True, verbose_name='Дата заказа')
    delivery_info = models.CharField(max_length=500, verbose_name='Информация о доставке', null=True, blank=True)
    order_price = models.DecimalField(max_digits=7, decimal_places=2, verbose_name='Цена заказа')
    admin_check = models.ForeignKey(User, verbose_name='Заявка принята работником:', on_delete=models.PROTECT,
                                    null=True, blank=True)
    deliver = models.BooleanField(verbose_name='Доставить по адресу', default=False)
    status = models.ForeignKey(OrderStatus, blank=True, on_delete=models.DO_NOTHING, verbose_name='Статус заказа')
    delivery_price = models.IntegerField(verbose_name='Стомость доставки', default=0, blank=True, null=True)
    payment = models.ForeignKey(Payment, on_delete=models.DO_NOTHING, verbose_name='Вид оплаты', blank=True, null=True)
    payment_url = models.URLField(verbose_name='Ссылка на оплату Авангард', blank=True, null=True)
    extra_payment_url = models.URLField(verbose_name='Дополнительная ссылка на оплату Авангард', blank=True, null=True)
    payed = models.BooleanField(verbose_name='Оплачены товары', default=False)
    payed_delivery = models.BooleanField(verbose_name='Оплачена доставка', default=False)
    tracing_num = models.CharField(max_length=30, verbose_name='Трек номер', null=True, blank=True)
    manager_message_id = models.IntegerField(verbose_name='Номер сообщения в канале менеджеров', default=0, blank=True,
                                             null=True)
    sale_type = models.CharField(max_length=50, verbose_name='Тип скидки', choices=SALE_TYPES, blank=False,
                                 default='no_sale')

    def __str__(self):
        return f'{self.id}'

    def update_order_sum(self, order_carts):
        order_sum = 0
        for item in order_carts:
            item.price = item.product.price
            order_sum += item.amount * item.price
        return order_sum

    def add_product(self, product_id: int, add_amount: int):
        add_product = Product.objects.get(id=product_id)
        Carts.objects.create(profile=self.profile, product=add_product, amount=add_amount, price=add_product.price,
                             order=self)
        order_carts = self.carts_set.all()
        self.order_price = self.update_order_sum(order_carts)
        self.save()

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
            if new_status in ["0", "6", "7"]:
                rests_action = 'add'
            elif self.status.title in ["0", "7"]:
                rests_action = 'remove'
            self.status = OrderStatus.objects.filter(title=new_status)[0]
            self.save()
        return rests_action

    class Meta:
        db_table = 'orders'
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'
