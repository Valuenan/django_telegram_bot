from django.urls import path
from . import views

urlpatterns = [
    path('set-csrf-token', views.set_csrf_token, name='set_csrf_token'),
    path('login', views.login_user, name='login_user'),
    path('logout', views.logout_view, name='logout'),
    path('', views.user, name='user'),
    path('catalog', views.catalog, name='products catalog'),
    # path('cart', views.cart, name='user cart'),
    path('profile', views.profile, name='user profile'),
    path('user/<int:pk>', views.user, name='user info'),
    path('user_edit', views.user_edit, name='user edit'),
]