from django.contrib import admin

from .models import Profile, Carts, Orders, OrderStatus


@admin.register(Profile)
class ProductsAdmin(admin.ModelAdmin):
    pass


@admin.register(Carts)
class ProductsAdmin(admin.ModelAdmin):
    pass


@admin.register(OrderStatus)
class ProductsAdmin(admin.ModelAdmin):
    pass


@admin.register(Orders)
class ProductsAdmin(admin.ModelAdmin):
    pass
