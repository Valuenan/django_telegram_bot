from django.contrib import admin

from .models import Profile, Carts, Orders, OrderStatus, Payment


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ['telegram_name', 'chat_id']
    search_fields = ['chat_id']


@admin.register(Carts)
class CartsAdmin(admin.ModelAdmin):
    pass


@admin.register(OrderStatus)
class OrderStatusAdmin(admin.ModelAdmin):
    pass


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    pass


@admin.register(Orders)
class ProductsAdmin(admin.ModelAdmin):
    pass
