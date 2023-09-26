from django.contrib import admin
from .models import Category, Product, File, Rests, Shop, Image, RestsOdataLoad


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
    search_fields = ['id']


@admin.register(Image)
class ImageAdmin(admin.ModelAdmin):
    list_display = ['name', 'ref_key']
    search_fields = ['name']
    ordering = ['name']


@admin.register(Product)
class ProductsAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'price', 'image', 'ref_key']
    search_fields = ['name', 'ref_key']
    ordering = ['category']


@admin.register(Rests)
class RestsAdmin(admin.ModelAdmin):
    list_display = ['shop', 'product', 'amount']
    search_fields = ['product__name']
    ordering = ['product__name']


@admin.register(RestsOdataLoad)
class RestsOdataLoadAdmin(admin.ModelAdmin):
    pass
