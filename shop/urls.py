from django.urls import path

from shop.views import OrdersList, OrderDetail

urlpatterns = [
    path('', OrdersList.as_view(), name='orders_list'),
    path('order/<int:pk>', OrderDetail.as_view(), name='orders_detail'),
]