from django.db.models import Sum
from rest_framework import serializers
from django.core.paginator import Paginator

from shop.models import Product, Category, Image, Rests, DiscountGroup, BotMainMessage
from users.models import Carts, Profile, OrderStatus, Payment, Orders

ORDER_STATUS_MAP = dict((
    ('0', 'Заявка обрабатывается'),
    ('1', 'Ожидается оплата'),
    ('2', 'Сборка заказа'),
    ('3', 'Доставка'),
    ('4', 'Ожидает в пункте выдачи'),
    ('5', 'Получен'),
    ('6', 'Отменен'),
    ('7', 'Предзаказ')
))

PAYMENT_MAP = dict((
    ('0', 'Карта'),
    ('1', 'QR код'),
    ('2', 'Перевод'),
))


class ImageSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = Image
        fields = ['id', 'url']

    def get_url(self, obj):
        request = self.context.get('request')
        filename = obj.name if obj.name else 'no-image.jpg'
        path = f"/static/products/{filename}"

        if request:
            return request.build_absolute_uri(path)
        return path


class RestsSerializer(serializers.ModelSerializer):
    shop = serializers.ReadOnlyField(source='shop.name')
    shop_active_discount = serializers.ReadOnlyField(source='shop.sale_type')

    class Meta:
        model = Rests
        fields = ['shop', 'amount', 'shop_active_discount']


class DiscountGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = DiscountGroup
        fields = '__all__'


class ProductSerializer(serializers.ModelSerializer):
    image = ImageSerializer(read_only=True)
    rests = RestsSerializer(source='rests_set', many=True, read_only=True)
    discount_group = DiscountGroupSerializer(read_only=True)
    is_tracked = serializers.SerializerMethodField()
    breadcrumbs = serializers.SerializerMethodField()

    def get_breadcrumbs(self, obj):
        if obj.category:
            return obj.category.get_breadcrumb_names()
        return []

    def get_image_data(self, obj):
        request = self.context.get('request')

        if obj.image and obj.image.name:
            filename = obj.image.name
        else:
            filename = 'no-image.jpg'

        path = f"/static/products/{filename}"

        url = request.build_absolute_uri(path) if request else path

        return {
            "id": obj.image.id if obj.image else None,
            "url": url
        }

    class Meta:
        model = Product
        fields = '__all__'

    def get_is_tracked(self, obj):
        chat_id = self.context.get('chat_id')
        if not chat_id:
            return False

        return obj.profile_set.filter(chat_id=chat_id).exists()


class CategorySerializer(serializers.ModelSerializer):
    '''Вывод корневой категории и дочерних'''
    children = serializers.SerializerMethodField()
    breadcrumbs = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ['command', 'ref_key', 'id', 'parent_category', 'hide', 'children', 'breadcrumbs']

    def has_products_with_rests(self, obj):
        products_with_stock = obj.products.filter(
            rests__amount__gt=0
        ).exists()

        if products_with_stock:
            return True

        for child in obj.children.filter(hide=False):
            if self.has_products_with_rests(child):
                return True

        return False

    def get_children(self, obj):
        children_queryset = obj.children.filter(hide=False)
        data = CategorySerializer(children_queryset, many=True, context=self.context).data
        return [item for item in data if item is not None]

    def to_representation(self, instance):
        if not self.has_products_with_rests(instance):
            return None
        return super().to_representation(instance)

    def get_breadcrumbs(self, obj):
        result = []
        curr = obj
        while curr is not None:
            result.insert(0, {'id': curr.id, 'command': curr.command})
            curr = curr.parent_category
        return result


class CartSerializer(serializers.ModelSerializer):
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = Carts
        fields = [
            'id', 'date', 'profile', 'product',
            'amount', 'price', 'order',
            'preorder', 'soft_delete', 'total_price'
        ]
        read_only_fields = ['id', 'date', 'total_price']

    def get_total_price(self, obj):
        return obj.amount * obj.price

    def validate(self, data):
        product = data.get('product')
        requested_amount = data.get('amount')

        total_rest = Rests.objects.filter(product=product).aggregate(
            total=Sum('amount')
        )['total'] or 0

        if requested_amount > total_rest:
            raise serializers.ValidationError({
                "amount": f"Недостаточно товара. В наличии: {total_rest}, а вы указали: {requested_amount}"
            })

        return data


class CartReadSerializer(CartSerializer):
    product = ProductSerializer(read_only=True)


class ProfileBaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        read_only_fields = ['id', 'date', 'chat_id']


class ProfileSerializer(ProfileBaseSerializer):
    class Meta(ProfileBaseSerializer.Meta):
        fields = [
            'id', 'date', 'telegram_name', 'first_name', 'last_name',
            'phone', 'chat_id', 'discount', 'delivery',
            'main_shop', 'delivery_street', 'preorder', 'preorder_selector'
        ]


class ProfileFavoritesSerializer(ProfileBaseSerializer):
    track = serializers.SerializerMethodField()

    class Meta(ProfileBaseSerializer.Meta):
        fields = [
            'id', 'date', 'telegram_name', 'first_name',
            'last_name', 'chat_id', 'track'
        ]

    def get_track(self, obj):
        request = self.context.get('request')
        chat_id = self.context.get('chat_id')

        if not request:
            return {"results": [], "next": None}

        page_number = request.query_params.get('page', 1)
        page_size = 10

        all_tracks = obj.track.all().order_by('id')
        paginator = Paginator(all_tracks, page_size)

        try:
            page_obj = paginator.get_page(page_number)

            serializer = ProductSerializer(
                page_obj,
                many=True,
                context={
                    'request': request,
                    'chat_id': chat_id
                }
            )

            return {
                'count': paginator.count,
                'next': page_obj.next_page_number() if page_obj.has_next() else None,
                'results': serializer.data
            }
        except Exception as e:
            return {"results": [], "next": None}


class OrderStatusSerializer(serializers.ModelSerializer):
    title = serializers.SerializerMethodField()

    class Meta:
        model = OrderStatus
        fields = '__all__'

    def get_title(self, obj):
        return ORDER_STATUS_MAP.get(obj.title, obj.title)


class PaymentSerializer(serializers.ModelSerializer):
    title = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = '__all__'

    def get_title(self, obj):
        return PAYMENT_MAP.get(obj.title, obj.title)


class OrderSerializer(serializers.ModelSerializer):
    carts = CartReadSerializer(many=True, read_only=True)
    status_details = OrderStatusSerializer(source='status', read_only=True)
    payment_details = PaymentSerializer(source='payment', read_only=True)

    class Meta:
        model = Orders
        exclude = ['manager_message_id', 'admin_check']


class MainMessageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = BotMainMessage
        fields = [
            'id', 'title', 'text', 'image', 'image_url',
            'is_active', 'priority', 'updated_at'
        ]

    def get_image_url(self, obj):
        if obj.image:
            return obj.image.url
        return None
