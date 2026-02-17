from django.urls import path
from . import views

urlpatterns = [
    path('user/', views.user, name='user_me'),  # Для получения своего профиля через TWA
    path('user/<int:pk>/', views.user, name='user_detail'),  # Для получения по ID

    path('set-csrf-token/', views.set_csrf_token, name='set_csrf_token'),
    path('login/', views.login_user, name='login_user'),
    path('logout/', views.logout_view, name='logout'),

    path('catalog/', views.catalog, name='products_catalog'),
    path('profile/', views.profile, name='user_profile'),
    path('user_edit/', views.user_edit, name='user_edit'),
]