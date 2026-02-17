"""django_telegram_bot URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
import os

from django.contrib import admin
from django.conf.urls import static
from django.urls import path, include, re_path
from django_telegram_bot import settings
from shop.views import ImportGoodsView, ImportCategory1CView, ImportProducts1CView, RemoveDuplicates, \
    RemoveNoRefKey, ImportImages1CView, ImportPrices1CView, ImportRests1CView, ProductsCheckList, MarkProductsSale, \
    PhotoCheckList
from django.views.static import serve as mediaserve
from django.views.generic import TemplateView

from shop.telegram.bot import webhook
from django.conf import settings
from api.views import set_csrf_token

urlpatterns = [
    path(settings.BOT_TOKEN + '/', webhook, name='webhook'),
    path('manager/', include('shop.urls')),
    path('api/', include('api.urls')),
    re_path(r'^assets/(?P<path>.*)$', mediaserve, {'document_root': os.path.join(settings.BASE_DIR, 'frontend/dist/assets')}),

    path('admin/import_goods/', ImportGoodsView.as_view(), name='admin_import_goods'),
    path('admin/load_from_1c', ImportCategory1CView.as_view(), name='load_from_1c'),
    path('admin/load_category_from_1c', ImportCategory1CView.as_view(), name='load_category_from_1c'),
    path('admin/load_products_from_1c', ImportProducts1CView.as_view(), name='load_products_from_1c'),
    path('admin/load_prices_from_1c', ImportPrices1CView.as_view(), name='load_prices_from_1c'),
    path('admin/load_rests_from_1c', ImportRests1CView.as_view(), name='load_rests_from_1c'),
    path('admin/load_images_from_1c', ImportImages1CView.as_view(), name='load_images_from_1c'),
    path('admin/mark_sale', MarkProductsSale.as_view(), name='mark_sale'),
    path('admin/remove_duplicates', RemoveDuplicates.as_view(), name='remove_duplicates'),
    path('admin/remove_no_ref_key', RemoveNoRefKey.as_view(), name='remove_no_ref_key'),
    path('admin/products_checklist', ProductsCheckList.as_view(), name='products_checklist'),
    path('admin/photo_checklist', PhotoCheckList.as_view(), name='photo_checklist'),
    path('admin/', admin.site.urls, name='admin'),

    path('set-csrf-token/', set_csrf_token, name='set-csrf-token'),
    path('__debug__/', include('debug_toolbar.urls')),
    path('', include('users.urls')),
]

# 1. СНАЧАЛА добавляем статику и медиа (обязательно ДО re_path)
if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [path('__debug__/', include(debug_toolbar.urls))] + urlpatterns
    urlpatterns += static.static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    urlpatterns += [
        re_path(f'^{settings.MEDIA_URL.lstrip("/")}(?P<path>.*)$',
            mediaserve, {'document_root': settings.MEDIA_ROOT}),
        re_path(f'^{settings.STATIC_URL.lstrip("/")}(?P<path>.*)$',
            mediaserve, {'document_root': settings.STATIC_ROOT}),
    ]

# 2. И в самом КОНЦЕ — ловушка для Vue (обрабатывает всё остальное)
urlpatterns += [
    re_path(r'^.*$', TemplateView.as_view(template_name="index.html"), name='home'),
]
