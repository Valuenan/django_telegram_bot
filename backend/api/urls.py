from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r'main-messages', views.MainMessageViewSet)
router.register(r'cart', views.CartViewSet, basename='cart')
router.register(r'orders', views.OrderViewSet, basename='orders')

urlpatterns = [
    path('profile/<int:chat_id>/', views.ProfileDetailView.as_view(), name='profile-detail'),
    path('profile/update/', views.ProfileUpdateAPIView.as_view(), name='profile-update'),
    path('profile/track/', views.TrackProductAPIView.as_view(), name='profile-track'),
    path('catalog', views.CategoryListView.as_view(), name='category-catalog'),
    path('category/<int:pk>/', views.CategoryDetailView.as_view(), name='category-detail'),
    path('products', views.ProductListView.as_view(), name='products-catalog'),
    path('product/<int:pk>/', views.ProductDetailView.as_view(), name='product-detail'),
    path('', include(router.urls)),
]