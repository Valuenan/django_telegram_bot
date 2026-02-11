from django_filters import rest_framework as filters
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q

from shop.models import Product, Category
from rest_framework.response import Response


class MainPagination(PageNumberPagination):
    page_size = 13
    max_page_size = 40

    def get_paginated_response(self, data):
        return Response({
            'links': {
                'next': self.get_next_link(),
                'previous': self.get_previous_link()
            },
            'count': self.page.paginator.count,
            'results': data
        })


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


class CharFilterInFilter(filters.BaseInFilter, filters.CharFilter):
    pass


class ProductFilter(filters.FilterSet):
    category = CharFilterInFilter(field_name='genres__name', lookup_expr='in')

    class Meta:
        model = Product
        fields = ['category']


class CategoryNullFilterBackend(filters.BaseInFilter):
    def filter_queryset(self, request, queryset, view):
        if 'parent_category' not in request.query_params:

            return queryset.filter(Q(parent_category__isnull=True))
        else:
            return queryset.filter(Q(parent_category=request.query_params['parent_category']))
