from rest_framework import serializers
from orders.models import Order, OrderItem, Cart, CartItem
from khaja.models import  CustomMeal
from khaja.serializers import CustomMealSerializer

class OrderItemSerializer(serializers.ModelSerializer):
    custom_meal_details = CustomMealSerializer(source='custom_meal', read_only=True)
    total_price = serializers.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        read_only=True, 
        source='get_total_price'
    )

    class Meta:
        model = OrderItem
        fields = [
            'id', 'custom_meal', 'custom_meal_details', 'meal_type', 
            'meal_category', 'no_of_servings', 'preferences', 
            'subscription_plan', 'delivery_time', 'price_per_serving',
            'quantity', 'meal_items_snapshot', 'total_price'
        ]


class OrderSerializer(serializers.ModelSerializer):
    order_items = OrderItemSerializer(many=True, read_only=True)
    user_name = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'user', 'user_name', 'created_at', 'updated_at',
            'subtotal', 'tax', 'delivery_charge', 'total_price',
            'status', 'payment_method', 'payment_status',
            'delivery_address', 'delivery_time', 'notes', 'order_items'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at', 
                           'subtotal', 'tax', 'delivery_charge', 'total_price']


class OrderCreateSerializer(serializers.Serializer):
    delivery_address = serializers.CharField()
    delivery_time = serializers.DateTimeField()
    payment_method = serializers.ChoiceField(choices=Order.PAYMENT_METHOD)
    notes = serializers.CharField(required=False, allow_blank=True)


# ===================== CART SERIALIZERS =====================

class CartItemSerializer(serializers.ModelSerializer):
    custom_meal_details = CustomMealSerializer(source='custom_meal', read_only=True)
    price_per_item = serializers.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        read_only=True, 
        source='get_price_per_item'
    )
    total_price = serializers.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        read_only=True, 
        source='get_total_price'
    )
    
    custom_meal_id = serializers.IntegerField(write_only=True, required=False)

    class Meta:
        model = CartItem
        fields = [
            'id', 'custom_meal', 'custom_meal_id', 'custom_meal_details',
            'quantity', 'price_per_item', 'total_price', 'added_at'
        ]
        read_only_fields = ['id', 'added_at']

    def create(self, validated_data):
        custom_meal_id = validated_data.pop('custom_meal_id', None)
        
        if custom_meal_id:
            custom_meal = CustomMeal.objects.get(combo_id=custom_meal_id)
            validated_data['custom_meal'] = custom_meal
        
        return super().create(validated_data)


class CartSerializer(serializers.ModelSerializer):
    cart_items = CartItemSerializer(many=True, read_only=True)
    subtotal = serializers.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        read_only=True, 
        source='get_subtotal'
    )
    tax = serializers.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        read_only=True, 
        source='get_tax'
    )
    delivery_charge = serializers.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        read_only=True, 
        source='get_delivery_charge'
    )
    total_price = serializers.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        read_only=True, 
        source='get_total_price'
    )
    items_count = serializers.IntegerField(read_only=True, source='get_items_count')

    class Meta:
        model = Cart
        fields = [
            'id', 'user', 'cart_items', 'subtotal', 'tax', 
            'delivery_charge', 'total_price', 'items_count', 
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']