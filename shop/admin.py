from django.contrib import admin
from .models import Category, Product, File, Rests, Shop


@admin.register(File)
class FileAdmin(admin.ModelAdmin):
    readonly_fields = ('user', 'file', 'created_at')
    list_display = ['created_at', 'user', 'file']
    ordering = ['created_at']
    search_fields = ['user']


@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    pass


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['command', 'parent_category']
    search_fields = ['command']


@admin.register(Product)
class ProductsAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'price', 'img']
    search_fields = ['name']
    ordering = ['category']


@admin.register(Rests)
class RestsAdmin(admin.ModelAdmin):
    list_display = ['shop', 'product', 'amount']
