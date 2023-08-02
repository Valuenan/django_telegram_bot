from django.urls import path

from shop.views import OrdersList, OrderDetail, OrdersHistory

urlpatterns = [
    path('', OrdersList.as_view(), name='orders_list'),
    path('history', OrdersHistory.as_view(), name='orders_history'),
    path('order/<int:pk>', OrderDetail.as_view(), name='orders_detail'),
]