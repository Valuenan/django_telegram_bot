from django.contrib.auth.models import User
from django.db import models


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

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'shops'
        verbose_name = 'Магазин'
        verbose_name_plural = 'Магазины'


class Category(models.Model):
    command = models.CharField(max_length=100, verbose_name='Название категории')
    id = models.IntegerField(unique=True, primary_key=True, db_index=True, verbose_name="ИД группы")
    parent_category = models.ForeignKey('self', on_delete=models.PROTECT, verbose_name='Родительсая категоря',
                                        null=True, blank=True)

    def __str__(self):
        return self.command

    class Meta:
        db_table = 'categories'
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'


class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.PROTECT, verbose_name='Категория')
    name = models.CharField(max_length=100, verbose_name='Название')
    img = models.CharField(max_length=100, verbose_name='Изображение товара', default='no-image.jpg')
    price = models.DecimalField(max_digits=7, decimal_places=2, verbose_name='Цена товара')

    def __str__(self):
        return self.name

    def edit_rests(self, action, shop, old_amount, new_amount):
        rest = self.rests_set.filter(shop=shop)[0]
        if action == 'add':
            rest.amount += old_amount
            rest.save()
        elif action == 'remove':
            rest.amount -= new_amount
            rest.save()

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

    def change_rests(self, shop, product, amount):
        pass

    class Meta:
        db_table = 'rests'
        verbose_name = 'Остаток'
        verbose_name_plural = 'Остатки'
