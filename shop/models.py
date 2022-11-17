from django.contrib.auth.models import User
from django.db import models


class File(models.Model):
    user = models.ForeignKey(User, on_delete=models.DO_NOTHING, verbose_name='Загруженно')
    file = models.FileField(upload_to='import/', verbose_name='Файл импорта')
    created_at = models.DateField(auto_now_add=True, verbose_name='Дата импорта')

    def __str__(self):
        return f'{self.user.username} - {self.created_at}'

    class Meta:
        db_table = 'files'
        verbose_name = 'Файл загрузки'
        verbose_name_plural = 'Файлы загрузки'


class Category(models.Model):
    command = models.CharField(max_length=100, verbose_name='Название категории')
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
    rests_prachecniy = models.DecimalField(max_digits=6, decimal_places=3, verbose_name='Остатки на Прачечном', default=0)
    rests_kievskaya = models.DecimalField(max_digits=6, decimal_places=3, verbose_name='Остатки на Киевской', default=0)

    def __str__(self):
        return f'{self.name} - {self.price}р. - остатки {self.rests_kievskaya}/{self.rests_prachecniy}'

    class Meta:
        db_table = 'products'
        verbose_name = 'Товар'
        verbose_name_plural = 'Товары'
