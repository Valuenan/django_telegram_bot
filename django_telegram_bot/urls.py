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
from django.contrib import admin
from django.conf.urls import url, static
from django.urls import path, include
from django_telegram_bot import settings
from shop.views import ImportGoodsView, Login, Logout, ImportCategory1CView, ImportProducts1CView, RemoveDuplicates, \
    RemoveNoRefKey, ImportImages1CView, ImportPrice1CView
from django.views.static import serve as mediaserve


urlpatterns = [
    path('login/', Login.as_view(), name='login'),
    path('logout/', Logout.as_view(), name='logout'),
    path('admin/import_goods/', ImportGoodsView.as_view(), name='admin_import_goods'),

    path('admin/load_from_1c', ImportCategory1CView.as_view(), name='load_from_1c'),
    path('admin/load_category_from_1c', ImportCategory1CView.as_view(), name='load_category_from_1c'),
    path('admin/load_products_from_1c', ImportProducts1CView.as_view(), name='load_products_from_1c'),
    path('admin/load_prices_from_1c', ImportPrice1CView.as_view(), name='load_prices_from_1c'),
    path('admin/load_images_from_1c', ImportImages1CView.as_view(), name='load_images_from_1c'),
    path('admin/remove_duplicates', RemoveDuplicates.as_view(), name='remove_duplicates'),
    path('admin/remove_no_ref_key', RemoveNoRefKey.as_view(), name='remove_no_ref_key'),

    path('admin/', admin.site.urls, name='admin'),
    path('', include('shop.urls')),
    path('__debug__/', include('debug_toolbar.urls')),
]

if settings.DEBUG:
    import debug_toolbar

    urlpatterns = [
                      path('__debug__/', include(debug_toolbar.urls)),
                  ] + urlpatterns

    urlpatterns += static.static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

else:
    urlpatterns += [
        url(f'^{settings.MEDIA_URL.lstrip("/")}(?P<path>.*)$',
            mediaserve, {'document_root': settings.MEDIA_ROOT}),
        url(f'^{settings.STATIC_URL.lstrip("/")}(?P<path>.*)$',
            mediaserve, {'document_root': settings.STATIC_ROOT}),
    ]
