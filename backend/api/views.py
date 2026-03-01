from django.contrib.auth.models import User
from django import db
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, viewsets, status
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.db.models import Sum, F, Prefetch
from rest_framework.views import APIView
from django.core.cache import cache
from init_data_py import InitData

from rest_framework_simplejwt.authentication import JWTAuthentication
from shop.models import Product, Category, Rests, BotMainMessage
from users.models import Carts, Profile, Orders, OrderStatus
from .serializers import (
    ProductSerializer, CategorySerializer, CartSerializer, CartReadSerializer, ProfileFavoritesSerializer,
    ProfileSerializer, OrderSerializer, MainMessageSerializer
)
from .service import MainPagination
from shop.telegram.bot import message_to_manager
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken


@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def telegram_auth(request):
    init_data_raw = request.data.get('initData')

    if not init_data_raw:
        return Response({"error": "No data"}, status=400)

    try:
        init_data = InitData.parse(init_data_raw)
        init_data.validate(settings.BOT_TOKEN)

        tg_user = init_data.user
        tg_id = str(tg_user.id)

        user, _ = User.objects.get_or_create(username=str(init_data.user.id))

        profile, created = Profile.objects.get_or_create(chat_id=tg_id)

        refresh = RefreshToken.for_user(user)

        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'is_new': created
        })
    except Exception as e:
        print(f"!!! ОШИБКА: {e}")
        return Response({"error": str(e)}, status=403)


class MainMessageViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Эндпоинт для получения сообщений главной страницы.
    Отдает только активные сообщения, отсортированные по приоритету.
    """
    permission_classes = [AllowAny]
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

    def get_sub_categories_recursive(self, category_id):
        """Рекурсивно собирает ID всех вложенных категорий (включая саму категорию)"""
        category_ids = [category_id]

        child_ids = Category.objects.filter(
            parent_category_id=category_id,
            hide=False
        ).values_list('id', flat=True)

        for child_id in child_ids:
            category_ids.extend(self.get_sub_categories_recursive(child_id))

        return list(set(category_ids))

    def get_queryset(self):
        chat_id = self.request.user.username
        category_id = self.request.query_params.get('category')

        is_preorder = False
        if chat_id:
            is_preorder = Profile.objects.filter(chat_id=chat_id, preorder=True).exists()

        queryset = Product.objects.select_related('image', 'category', 'discount_group')

        if category_id:
            all_ids = self.get_sub_categories_recursive(category_id)
            queryset = queryset.filter(category_id__in=all_ids)

        rests_filter_qs = Rests.objects.select_related('shop')
        if not is_preorder:
            queryset = queryset.filter(rests__amount__gt=0).distinct()
            rests_filter_qs = rests_filter_qs.filter(amount__gt=0)

        active_rests = Prefetch('rests_set', queryset=rests_filter_qs)
        return queryset.prefetch_related(active_rests).order_by('id')

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['chat_id'] = self.request.user.username
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
        context['chat_id'] = self.request.user.username
        return context


class CategoryListView(generics.ListAPIView):
    '''Вывод списка родительских категорий'''
    serializer_class = CategorySerializer
    permission_classes = [permissions.DjangoModelPermissionsOrAnonReadOnly]
    pagination_class = MainPagination
    ordering = ['id']

    def get_queryset(self):
        chat_id = self.request.user.username

        is_preorder = False
        if chat_id:
            is_preorder = Profile.objects.filter(chat_id=chat_id, preorder=True).exists()

        rests_qs = Rests.objects.all()
        if not is_preorder:
            rests_qs = rests_qs.filter(amount__gt=0)

        return Category.objects.filter(
            hide=False,
            parent_category__isnull=True
        ).prefetch_related(
            'children',
            Prefetch('products__rests_set', queryset=rests_qs)
        )

    def list(self, request, *args, **kwargs):
        chat_id = self.request.user.username

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
        chat_id = self.request.user.username

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
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        tg_id = self.request.user.username
        profile = get_object_or_404(Profile, chat_id=tg_id)

        queryset = Carts.objects.filter(
            profile=profile,
            soft_delete=False,
            order__isnull=True
        )

        if not profile.preorder:
            queryset = queryset.filter(preorder=False)

        return queryset.order_by('preorder')

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({"chat_id": self.request.user.username})
        return context

    def get_serializer_class(self):
        if self.action in ['list', 'retrieve']:
            return CartReadSerializer
        return CartSerializer

    def create(self, request, *args, **kwargs):
        tg_id = request.user.username
        product_id = request.data.get('product')
        amount = request.data.get('amount', 1)
        preorder = request.data.get('preorder')

        if not product_id:
            return Response(
                {"error": "Требуется product_id"},
                status=status.HTTP_400_BAD_REQUEST
            )

        profile = get_object_or_404(Profile, chat_id=tg_id)

        update_defaults = {
            'amount': amount,
            'price': request.data.get('price'),
        }

        if preorder is not None:
            update_defaults['preorder'] = preorder

        cart_item, created = Carts.objects.update_or_create(
            profile=profile,
            product_id=product_id,
            soft_delete=False,
            order__isnull=True,
            defaults=update_defaults
        )

        serializer = CartReadSerializer(cart_item, context={'request': request})
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()

        total_carts_sum = queryset.filter(preorder=False).aggregate(
            total=Sum(F('amount') * F('price'))
        )['total'] or 0

        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'total_carts_sum': total_carts_sum,
            'results': serializer.data
        })


class ProfileDetailView(generics.RetrieveUpdateAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = ProfileSerializer

    def get_object(self):
        return get_object_or_404(Profile, chat_id=self.request.user.username)

    def get_serializer_class(self):
        if self.request.query_params.get('with_track') == 'true':
            return ProfileFavoritesSerializer
        return ProfileSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({
            "request": self.request,
            "chat_id": self.request.user.username
        })
        return context


class ProfileUpdateAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        profile = get_object_or_404(Profile, chat_id=request.user.username)

        serializer = ProfileSerializer(profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def post(self, request):
        return self.patch(request)


class TrackProductAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        tg_id = request.user.username
        product_id = request.data.get('product_id')

        if not product_id:
            return Response({"error": "product_id is required"}, status=400)

        profile = get_object_or_404(Profile, chat_id=tg_id)
        product = get_object_or_404(Product, id=product_id)

        if product in profile.track.all():
            profile.track.remove(product)
            action = "removed"
        else:
            profile.track.add(product)
            action = "added"

        return Response({"status": "success", "action": action}, status=status.HTTP_200_OK)


class OrderViewSet(viewsets.ModelViewSet):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = OrderSerializer

    def get_queryset(self):
        tg_id = self.request.user.username
        return Orders.objects.filter(profile__chat_id=tg_id) \
            .select_related('status', 'payment') \
            .prefetch_related('carts__product') \
            .order_by('-id')

    def create(self, request, *args, **kwargs):
        db.close_old_connections()

        with db.transaction.atomic():
            tg_id = request.user.username
            profile = get_object_or_404(Profile, chat_id=tg_id)

            cart_items = Carts.objects.filter(profile=profile, order__isnull=True, soft_delete=False)
            if not cart_items.exists():
                return Response({"error": "Корзина пуста"}, status=status.HTTP_400_BAD_REQUEST)

            delivery_street = request.data.get('delivery_info') or profile.delivery_street or "СПБ пер. Прачечный 3"
            preorder_mode = request.data.get('preorder')

        def create_single_order(items_to_add, target_status, order_price):
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
                order_ready = create_single_order(cart_items.filter(preorder=False), target_status='1',
                                                  order_price=request.data.get('order_price', 0))
                order_pre = create_single_order(cart_items.filter(preorder=True), target_status='8', order_price=0)
                if order_ready:
                    created_orders.append(order_ready)
                if order_pre:
                    created_orders.append(order_pre)

            elif preorder_mode == 'part-order':
                order = create_single_order(cart_items.filter(preorder=False), target_status='1',
                                            order_price=request.data.get('order_price', 0))
                if order:
                    created_orders.append(order)

            elif preorder_mode == 'part-preorder':
                order = create_single_order(cart_items.filter(preorder=True), target_status='8', order_price=0)
                if order:
                    created_orders.append(order)

            elif preorder_mode == 'preorder':
                cart_items.update(preorder=True)
                order = create_single_order(cart_items, target_status='8', order_price=0)
                if order:
                    created_orders.append(order)
        else:
            order = create_single_order(cart_items.filter(preorder=False), target_status='1',
                                        order_price=request.data.get('order_price', 0))
            if order: created_orders.append(order)

        for order in created_orders:
            try:
                items_text = "".join([f" - {item.product.name} ({item.amount} шт.)\n" for item in order.carts.all()])
                msg = (
                    f"🔔 Заказ №: {order.id}\n"
                    f"Клиент: {order.profile.telegram_name}\n"
                    f"Список товаров:\n{items_text}"
                    f"Адрес: {order.delivery_info}\n"
                    f"На сумму: {order.order_price} руб."
                )
                message_to_manager(msg)
            except Exception as e:
                print(f"Telegram Notification Error: {e}")

        if not created_orders:
            return Response({"error": "Нет товаров для заказа"}, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(created_orders, many=True) if len(created_orders) > 1 else self.get_serializer(
            created_orders[0])
        return Response(serializer.data, status=status.HTTP_201_CREATED)
