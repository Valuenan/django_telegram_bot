from django.contrib import admin

from .models import Profile, Carts, Orders, OrderStatus, Payment, UserMessage


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ['date', 'telegram_name', 'chat_id', 'phone', 'discount']
    search_fields = ['chat_id']


@admin.register(UserMessage)
class UserMessageAdmin(admin.ModelAdmin):
    list_display = ['user', 'manager', 'manager_signature', 'message', 'checked']
    search_fields = ['from_user']


@admin.register(Carts)
class CartsAdmin(admin.ModelAdmin):
    list_display = ['profile', 'product', 'order', 'soft_delete']
    search_fields = ['profile__telegram_name']


@admin.register(OrderStatus)
class OrderStatusAdmin(admin.ModelAdmin):
    pass


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    pass


@admin.register(Orders)
class OrdersAdmin(admin.ModelAdmin):
    list_display = ['id', 'date', 'profile', 'admin_check', 'payed']
    search_fields = ['id', 'profile__telegram_name']
