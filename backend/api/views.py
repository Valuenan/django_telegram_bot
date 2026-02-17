from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, viewsets, status
from rest_framework.response import Response
from django.db.models import Sum, F, Prefetch
from rest_framework.views import APIView
from django.core.cache import cache

from shop.models import Product, Category, Rests, BotMainMessage
from users.models import Carts, Profile, Orders, OrderStatus
from .serializers import (
    ProductSerializer, CategorySerializer, CartSerializer, CartReadSerializer, ProfileFavoritesSerializer,
    ProfileSerializer, OrderSerializer, MainMessageSerializer
)
from .service import MainPagination, CategoryNullFilterBackend
from shop.telegram.bot import message_to_manager
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie


@ensure_csrf_cookie
def set_csrf_token(request):
    """
    Эндпоинт для установки CSRF-куки на клиенте.
    Декоратор @ensure_csrf_cookie принудительно отправляет заголовок Set-Cookie.
    """
    return JsonResponse({'details': 'CSRF cookie set'}, status=200)


class MainMessageViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Эндпоинт для получения сообщений главной страницы.
    Отдает только активные сообщения, отсортированные по приоритету.
    """
    queryset = BotMainMessage.objects.filter(is_active=True)
    serializer_class = MainMessageSerializer
    pagination_class = None


class ProductListView(generics.ListAPIView):
    '''Вывод списка товаров'''
    serializer_class = ProductSerializer
    pagination_class = MainPagination

    def get_sub_categories(self, category_id):
        """Рекурсивно собирает ID всех дочерних категорий"""
        ids = [category_id]
        children = Category.objects.filter(parent_category_id=category_id, hide=False).values_list('id', flat=True)
        for child_id in children:
            ids.extend(self.get_sub_categories(child_id))
        return ids

    def get_queryset(self):
        chat_id = self.request.query_params.get('chat_id')
        category_id = self.request.query_params.get('category')

        # 1. Фильтрация остатков (Rests)
        rests_filter = Rests.objects.select_related('shop')
        show_out_of_stock = False
        if chat_id:
            profile = Profile.objects.filter(chat_id=chat_id).first()
            if profile and profile.preorder:
                show_out_of_stock = True

        if not show_out_of_stock:
            rests_filter = rests_filter.filter(amount__gt=0)

        active_rests = Prefetch(
            'rests_set',
            queryset=rests_filter
        )

        queryset = Product.objects.select_related('image', 'category', 'discount_group') \
            .prefetch_related(active_rests)

        if category_id:
            filtered_queryset = queryset.filter(category_id=category_id)

            if not filtered_queryset.exists():
                all_sub_ids = self.get_sub_categories(category_id)
                queryset = queryset.filter(category_id__in=all_sub_ids)
            else:
                queryset = filtered_queryset

        return queryset

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['chat_id'] = self.request.query_params.get('chat_id')
        return context


class ProductDetailView(generics.RetrieveAPIView):
    '''Вывод одиночного товаров'''
    serializer_class = ProductSerializer

    def get_queryset(self):
        active_rests = Prefetch(
            'rests_set',
            queryset=Rests.objects.filter(amount__gt=0).select_related('shop')
        )

        return Product.objects.select_related('image', 'category', 'discount_group') \
            .prefetch_related(active_rests)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['chat_id'] = self.request.query_params.get('chat_id')
        return context


class CategoryListView(generics.ListAPIView):
    '''Вывод списка родительских категорий'''
    serializer_class = CategorySerializer
    permission_classes = [permissions.DjangoModelPermissionsOrAnonReadOnly]
    pagination_class = MainPagination
    ordering = ['id']

    def get_queryset(self):
        chat_id = self.request.query_params.get('chat_id')

        # Проверяем флаг preorder у профиля
        is_preorder = False
        if chat_id:
            is_preorder = Profile.objects.filter(chat_id=chat_id, preorder=True).exists()

        # Настраиваем фильтр остатков
        rests_qs = Rests.objects.all()
        if not is_preorder:
            rests_qs = rests_qs.filter(amount__gt=0)

        # Собираем итоговый QuerySet
        return Category.objects.filter(
            hide=False,
            parent_category__isnull=True
        ).prefetch_related(
            'children',
            Prefetch('products__rests_set', queryset=rests_qs)
        )

    def list(self, request, *args, **kwargs):
        chat_id = request.query_params.get('chat_id')

        is_preorder = False
        if chat_id:
            is_preorder = Profile.objects.filter(chat_id=chat_id, preorder=True).exists()

        cache_suffix = "preorder" if is_preorder else "regular"
        cache_key = f'categories_tree_data_{cache_suffix}'

        cached_data = cache.get(cache_key)
        if cached_data:
            return Response(cached_data)

        response = super().list(request, *args, **kwargs)

        if isinstance(response.data, dict) and 'results' in response.data:
            data_to_cache = [item for item in response.data['results'] if item is not None]
        else:
            data_to_cache = [item for item in response.data if item is not None]

        cache.set(cache_key, data_to_cache, 3600)
        return Response(data_to_cache)


class CategoryDetailView(generics.RetrieveAPIView):
    '''Вывод одной категории'''
    serializer_class = CategorySerializer

    def get_queryset(self):
        chat_id = self.request.query_params.get('chat_id')

        is_preorder = False
        if chat_id:
            is_preorder = Profile.objects.filter(chat_id=chat_id, preorder=True).exists()

        rests_qs = Rests.objects.all()
        if not is_preorder:
            rests_qs = rests_qs.filter(amount__gt=0)

        return Category.objects.filter(hide=False).prefetch_related(
            Prefetch('children', queryset=Category.objects.filter(hide=False)),
            Prefetch('products__rests_set', queryset=rests_qs)
        )


class CartViewSet(viewsets.ModelViewSet):
    pagination_class = None

    def get_queryset(self):
        chat_id = self.request.query_params.get('chat_id')
        profile = get_object_or_404(Profile, chat_id=chat_id)
        if profile.preorder:
            queryset = Carts.objects.filter(soft_delete=False, order__isnull=True).order_by('preorder')
        else:
            queryset = Carts.objects.filter(soft_delete=False, order__isnull=True, preorder=False)

        if chat_id:
            return queryset.filter(profile__chat_id=chat_id, soft_delete=False, order__isnull=True)

        return queryset.none()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        chat_id = self.request.query_params.get('chat_id')
        context.update({"chat_id": chat_id})
        return context

    def get_serializer_class(self):
        if self.action in ['list', 'retrieve']:
            return CartReadSerializer
        return CartSerializer

    def create(self, request, *args, **kwargs):
        chat_id = request.data.get('chat_id')
        product_id = request.data.get('product')
        amount = request.data.get('amount', 1)
        preorder = request.data.get('preorder')

        if not chat_id or not product_id:
            return Response(
                {"error": "Требуются chat_id и product"},
                status=status.HTTP_400_BAD_REQUEST
            )

        profile = get_object_or_404(Profile, chat_id=chat_id)

        update_defaults = {
            'amount': amount,
            'price': request.data.get('price'),
        }

        if preorder is not None:
            update_defaults['preorder'] = preorder

        cart_item, created = Carts.objects.filter(
            soft_delete=False,
            order__isnull=True
        ).update_or_create(
            profile=profile,
            product_id=product_id,
            defaults=update_defaults
        )

        serializer = CartReadSerializer(cart_item, context={'request': request})

        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        total_carts_sum = queryset.filter(order__isnull=True, preorder=False).aggregate(
            total=Sum(F('amount') * F('price'))
        )['total'] or 0

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response = self.get_paginated_response(serializer.data)
            response.data['total_carts_sum'] = total_carts_sum
            return response

        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'total_carts_sum': total_carts_sum,
            'results': serializer.data
        })


class ProfileDetailView(generics.RetrieveUpdateAPIView):
    lookup_field = 'chat_id'

    def get_object(self):
        chat_id = self.kwargs.get('chat_id')
        profile = Profile.objects.filter(chat_id=chat_id).first()

        if not profile:
            profile = Profile.objects.create(
                chat_id=chat_id,
                first_name=self.request.query_params.get('first_name', ''),
                telegram_name=self.request.query_params.get('telegram_name', ''),
                preorder=False
            )
            profile.is_new_user = True
        else:
            profile.is_new_user = False

        return profile

    def get_serializer_class(self):
        if self.request.query_params.get('with_track') == 'true':
            return ProfileFavoritesSerializer
        return ProfileSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({
            "request": self.request,
            "chat_id": self.kwargs.get('chat_id')
        })
        return context


class ProfileUpdateAPIView(APIView):
    def patch(self, request):
        chat_id = request.data.get('chat_id')
        if not chat_id:
            return Response({"error": "chat_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        profile = get_object_or_404(Profile, chat_id=chat_id)

        serializer = ProfileSerializer(profile, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def post(self, request):
        return self.patch(request)


class TrackProductAPIView(APIView):
    def post(self, request):
        chat_id = request.data.get('chat_id')
        product_id = request.data.get('product_id')

        profile = get_object_or_404(Profile, chat_id=chat_id)
        product = get_object_or_404(Product, id=product_id)

        if product in profile.track.all():
            profile.track.remove(product)
            action = "removed"
        else:
            profile.track.add(product)
            action = "added"

        return Response({"status": "success", "action": action}, status=status.HTTP_200_OK)


class OrderViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = OrderSerializer

    def get_queryset(self):
        chat_id = self.request.query_params.get('chat_id')
        queryset = Orders.objects.select_related('status', 'payment').prefetch_related('carts__product')

        if chat_id:
            return queryset.filter(profile__chat_id=chat_id).order_by('-id')

        return queryset.none()

    def create(self, request, *args, **kwargs):
        chat_id = request.data.get('chat_id')
        profile = get_object_or_404(Profile, chat_id=chat_id)

        cart_items = Carts.objects.filter(profile=profile, order__isnull=True, soft_delete=False)

        if not cart_items.exists():
            return Response({"error": "Корзина пуста"}, status=status.HTTP_400_BAD_REQUEST)

        delivery_street = profile.delivery_street if request.data.get('deliver') else "СПБ пер. Прачечный 3"
        preorder_mode = request.data.get('preorder')

        def create_order(items_to_add, target_status, order_price):
            if not items_to_add.exists():
                return None

            new_order = Orders.objects.create(
                profile=profile,
                order_price=order_price,
                deliver=request.data.get('deliver', False),
                delivery_info=delivery_street,
                payment_id=f'{request.data.get("payment")}',
                status_id=target_status,
                sale_type=request.data.get('sale_type'),
            )
            items_to_add.update(order=new_order)
            return new_order

        created_orders = []
        if profile.preorder:
            if preorder_mode == 'split':
                order_ready = create_order(cart_items.filter(preorder=False), target_status='1',
                                           order_price=request.data.get('order_price'))
                order_pre = create_order(cart_items.filter(preorder=True), target_status='8', order_price=0)
                if order_ready:
                    created_orders.append(order_ready)
                if order_pre:
                    created_orders.append(order_pre)

            elif preorder_mode == 'part-order':
                order = create_order(cart_items.filter(preorder=False), target_status='1',
                                     order_price=request.data.get('order_price'))
                if order:
                    created_orders.append(order)

            elif preorder_mode == 'part-preorder':
                order = create_order(cart_items.filter(preorder=True), target_status='8', order_price=0)
                if order:
                    created_orders.append(order)

            elif preorder_mode == 'preorder':
                cart_items.update(preorder=True)
                order = create_order(cart_items, target_status='8', order_price=0)
                if order:
                    created_orders.append(order)
        else:
            order = create_order(cart_items.filter(preorder=False), target_status='1',
                                 order_price=request.data.get('order_price'))
            if order:
                created_orders.append(order)

        for order in created_orders:
            try:
                items_text = ""
                order_items = order.carts.all()
                for item in order_items:
                    items_text += f" - {item.product.name} ({item.amount} шт.)\n"

                msg = (
                    f"🔔 Заказ №: {order.id}\n"
                    f"Клиент: {order.profile.telegram_name}\n"
                    f"Список товаров:\n{items_text}"
                    f"Адрес: {order.delivery_info}\n"
                    f"На сумму: {order.order_price} руб."
                )

                message_to_manager(msg)
            except Exception as e:
                message_to_manager(f"Ошибка при формировании сообщения в канал: {e}")

        if not created_orders:
            return Response({"error": "Нет подходящих товаров для формирования заказа"},
                            status=status.HTTP_400_BAD_REQUEST)

        if len(created_orders) > 1:
            serializer = OrderSerializer(created_orders, many=True)
        else:
            serializer = OrderSerializer(created_orders[0])

        return Response(serializer.data, status=status.HTTP_201_CREATED)
