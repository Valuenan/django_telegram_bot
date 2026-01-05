from django.urls import path

from shop.telegram.bot import webhook
from shop.telegram.settings import TOKEN
from shop.views import OrdersList, OrderDetail, OrdersHistory, SendMessageToUser, UsersMessagesList, \
    UsersMessagesDetail, SendMessageToEveryone

urlpatterns = [
    path('', OrdersList.as_view(), name='orders_list'),
    path('history/', OrdersHistory.as_view(), name='orders_history'),
    path('order/<int:pk>', OrderDetail.as_view(), name='orders_detail'),
    path('send_message/', SendMessageToUser.as_view(), name='send_message'),
    path('user_messages/', UsersMessagesList.as_view(), name='user_messages_list'),
    path('user_messages/<int:pk>', UsersMessagesDetail.as_view(), name='user_messages_detail'),
    path('send_everyone/', SendMessageToEveryone.as_view(), name='send_everyone'),
    path(TOKEN + '/', webhook, name='webhook')
]