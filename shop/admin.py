from django.contrib import admin
from .models import Category, Product, File, Rests, Shop, Image, RestsOdataLoad, DiscountGroup


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
    list_display = ['command', 'parent_category', 'hide']
    search_fields = ['id', 'command', 'ref_key']
    sortable_by = ['hide']


@admin.register(Image)
class ImageAdmin(admin.ModelAdmin):
    list_display = ['name', 'ref_key']
    search_fields = ['name']
    ordering = ['name']


@admin.register(DiscountGroup)
class DiscountGroupAdmin(admin.ModelAdmin):
    list_display = ['name', 'trigger', 'regular_value', 'extra_value']


@admin.register(Product)
class ProductsAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'price', 'image', 'ref_key']
    search_fields = ['name', 'ref_key', 'search']
    ordering = ['category']


@admin.register(Rests)
class RestsAdmin(admin.ModelAdmin):
    list_display = ['shop', 'product', 'amount']
    search_fields = ['product__name']
    ordering = ['product__name']


@admin.register(RestsOdataLoad)
class RestsOdataLoadAdmin(admin.ModelAdmin):
    list_display = ['active', 'date_time', 'recorder', 'product_key', 'amount']
    search_fields = ['recorder', 'product_key']
    ordering = ['-date_time']
