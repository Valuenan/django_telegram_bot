from django.contrib import admin
from .models import Category, Product, File, Rests


@admin.register(File)
class FileAdmin(admin.ModelAdmin):
    readonly_fields = ('user', 'file', 'created_at')


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    pass


@admin.register(Product)
class ProductsAdmin(admin.ModelAdmin):
    pass

@admin.register(Rests)
class RestsAdmin(admin.ModelAdmin):
    pass

