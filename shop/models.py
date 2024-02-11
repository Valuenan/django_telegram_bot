from datetime import datetime

from django.contrib.auth.models import User
from django.db import models

SALE_TYPES = (
    ('no_sale', 'Нет скидки'),
    ('regular', 'Обычная скидка'),
    ('extra', 'Повышенная скидка'),
)


class File(models.Model):
    user = models.ForeignKey(User, on_delete=models.DO_NOTHING, verbose_name='Загруженно')
    file = models.FileField(upload_to='import/', verbose_name='Файл импорта')
    created_at = models.DateField(auto_now_add=True, verbose_name='Дата импорта')

    def __str__(self):
        return self.file

    class Meta:
        db_table = 'files'
        verbose_name = 'Файл загрузки'
        verbose_name_plural = 'Файлы загрузки'


class Shop(models.Model):
    name = models.CharField(max_length=100, verbose_name='Название магазина')
    sale_type = models.CharField(max_length=50, verbose_name='Тип скидки', choices=SALE_TYPES, blank=False,
                                 default='no_sale')

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'shops'
        verbose_name = 'Магазин'
        verbose_name_plural = 'Магазины'


class Category(models.Model):
    command = models.CharField(max_length=100, verbose_name='Название категории')
    ref_key = models.CharField(max_length=36, verbose_name='Ссылка в базе 1с', unique=True, null=True, blank=True)
    id = models.IntegerField(unique=True, primary_key=True, db_index=True, verbose_name="ИД группы")
    parent_category = models.ForeignKey('self', on_delete=models.CASCADE, verbose_name='Родительсая категоря',
                                        null=True, blank=True)
    hide = models.BooleanField(verbose_name='Скрыть категорию', default=False)

    def __str__(self):
        return f'{self.id}.{self.command}'

    class Meta:
        db_table = 'categories'
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'


class Image(models.Model):
    ref_key = models.CharField(max_length=36, verbose_name='Ссылка в базе 1с', unique=True, null=True, blank=True)
    name = models.CharField(max_length=50, verbose_name='Название файла с расширением')

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'image'
        verbose_name = 'Изображение'
        verbose_name_plural = 'Изображения'


class DiscountGroup(models.Model):
    name = models.CharField(verbose_name="Название", max_length=30)
    trigger = models.CharField(verbose_name="Символ в товаре", max_length=3)
    regular_value = models.DecimalField(verbose_name="Коэффициент скидки (%) (обычная)", max_digits=3, decimal_places=2,
                                        default=1)
    extra_value = models.DecimalField(verbose_name="Коэффициент скидки (%) (повышенная)", max_digits=3,
                                      decimal_places=2, default=1)

    def __str__(self):
        return str(self.name)

    class Meta:
        db_table = 'discount_group'
        verbose_name = 'Группа скидок'
        verbose_name_plural = 'Группы скидок'


class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, verbose_name='Категория', null=True, blank=True)
    ref_key = models.CharField(max_length=36, verbose_name='Ссылка в базе 1с', unique=True, null=True, blank=True)
    name = models.CharField(max_length=100, verbose_name='Название')
    image = models.ForeignKey(Image, on_delete=models.CASCADE, verbose_name='Изображение товара', null=True, blank=True)
    price = models.DecimalField(max_digits=7, decimal_places=2, verbose_name='Цена товара')
    search = models.IntegerField(verbose_name='Номер для поиска', null=True, blank=True)
    discount_group = models.ForeignKey(DiscountGroup, on_delete=models.SET_NULL, verbose_name='Категория скидки',
                                       null=True, blank=True)

    def __str__(self):
        return self.name

    def edit_rests(self, action, shop, old_amount, new_amount):
        rest = self.rests_set.filter(shop=shop)[0]
        if action == 'add':
            rest.amount += old_amount
            rest.save()
            odata = RestsOdataLoad.objects.filter(recorder=None, product_key=self.ref_key, amount=old_amount)
            odata[0].delete()
        elif action == 'remove':
            rest.amount -= new_amount
            rest.save()
            RestsOdataLoad.objects.create(active=True, date_time=datetime.now(), product_key=self.ref_key,
                                          amount=new_amount)

    class Meta:
        db_table = 'products'
        verbose_name = 'Товар'
        verbose_name_plural = 'Товары'


class Rests(models.Model):
    shop = models.ForeignKey(Shop, on_delete=models.PROTECT, verbose_name='Название магазина')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name='Товар')
    amount = models.DecimalField(max_digits=6, decimal_places=3, verbose_name='Количество', default=0)

    def __str__(self):
        return self.product.name

    class Meta:
        db_table = 'rests'
        verbose_name = 'Остаток'
        verbose_name_plural = 'Остатки'


class RestsOdataLoad(models.Model):
    active = models.BooleanField(verbose_name="Активно")
    date_time = models.DateTimeField(verbose_name="Дата и время документа")
    recorder = models.CharField(verbose_name="Ссылка на документ в 1с", max_length=36, null=True, blank=True)
    product_key = models.CharField(verbose_name="Ссылка на товар в 1с", max_length=36)
    amount = models.IntegerField(verbose_name='Количество', blank=True, null=True)
    line_number = models.IntegerField(verbose_name='Позиция в документе 1с', blank=True, null=True)

    def __str__(self):
        return f'{self.recorder}'

    class Meta:
        db_table = 'rests_odata_load'
        verbose_name = 'Данные загрузки остатков (не изменять)'
        verbose_name_plural = 'Данные загрузки остатков (не изменять)'
