from django.db import models


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
    img = models.SlugField(verbose_name='Изображение товара', default='no-image')
    price = models.IntegerField(verbose_name='Цена товара')
    rests_prachecniy = models.IntegerField(verbose_name='Остатки на Прачечном', default=0)
    rests_kievskaya = models.IntegerField(verbose_name='Остатки на Киевской', default=0)

    def __str__(self):
        return f'{self.name} - {self.price}р. - остатки {self.rests_kievskaya}/{self.rests_prachecniy}'

    class Meta:
        db_table = 'products'
        verbose_name = 'Товар'
        verbose_name_plural = 'Товары'
