# orders/serializers.py
from rest_framework import serializers
from orders.models import Order, OrderItem, ComboOrderItem, Cart, CartItem, ComboCartItem
from khaja.models import CustomMeal, Meals, Combo
from khaja.serializers import CustomMealSerializer, MealSerializer


class OrderItemSerializer(serializers.ModelSerializer):
    custom_meal_details = CustomMealSerializer(source='custom_meal', read_only=True)
    meal_details = MealSerializer(source='meals', read_only=True)
    delivery_time_slot_display = serializers.CharField(
        source='get_delivery_time_slot_display',
        read_only=True
    )
    time_slot_range = serializers.CharField(
        source='get_time_slot_range',
        read_only=True
    )
    formatted_delivery_time = serializers.CharField(
        source='get_formatted_delivery_time',
        read_only=True
    )
    total_price = serializers.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        read_only=True, 
        source='get_total_price'
    )

    class Meta:
        model = OrderItem
        fields = [
            'id', 'custom_meal', 'custom_meal_details', 'meals', 'meal_details',
            'meal_type', 'meal_category', 'no_of_servings', 'preferences', 
            'subscription_plan', 'delivery_time', 'delivery_time_slot',
            'delivery_time_slot_display', 'time_slot_range', 'formatted_delivery_time',
            'price_per_serving', 'quantity', 'meal_items_snapshot', 'total_price'
        ]


class ComboOrderItemSerializer(serializers.ModelSerializer):
    combo_name = serializers.SerializerMethodField()
    delivery_time_slot_display = serializers.CharField(
        source='get_delivery_time_slot_display',
        read_only=True
    )
    time_slot_range = serializers.CharField(
        source='get_time_slot_range',
        read_only=True
    )
    formatted_delivery_time = serializers.CharField(
        source='get_formatted_delivery_time',
        read_only=True
    )
    total_price = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        read_only=True,
        source='get_total_price'
    )
    
    class Meta:
        model = ComboOrderItem
        fields = [
            'id', 'combo', 'combo_name', 'subscription_plan',
            'delivery_from_date', 'delivery_to_date', 'delivery_time_slot',
            'delivery_time_slot_display', 'delivery_time', 'time_slot_range',
            'formatted_delivery_time', 'quantity', 'preferences', 
            'price_snapshot', 'combo_items_snapshot', 'total_price'
        ]
    
    def get_combo_name(self, obj):
        return f"Combo #{obj.combo.cid}"


class OrderSerializer(serializers.ModelSerializer):
    order_items = OrderItemSerializer(many=True, read_only=True)
    combo_items = ComboOrderItemSerializer(many=True, read_only=True)
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id', 'user', 'user_name', 'created_at', 'updated_at',
            'subtotal', 'tax', 'delivery_charge', 'total_price',
            'status', 'payment_status', 'payment_method',
            'delivery_address', 'notes', 'order_items', 'combo_items'
        ]
        read_only_fields = [
            'id', 'user', 'created_at', 'updated_at',
            'subtotal', 'tax', 'delivery_charge', 'total_price'
        ]
    
    def get_user_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}" if obj.user else "Guest"


class OrderCreateSerializer(serializers.Serializer):
    delivery_address = serializers.CharField(required=False) 
    payment_method = serializers.ChoiceField(choices=Order.PAYMENT_METHOD, required=False)
    notes = serializers.CharField(required=False, allow_blank=True) 
    cart_item_ids = serializers.ListField(
        child=serializers.IntegerField(), 
        required=False,
        help_text="List of regular cart item IDs to order"
    )
    combo_item_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        help_text="List of combo cart item IDs to order"
    )


class CartItemSerializer(serializers.ModelSerializer):
    custom_meal_details = CustomMealSerializer(source='custom_meal', read_only=True)
    meal_details = MealSerializer(source='meals', read_only=True)
    delivery_time_slot_display = serializers.CharField(
        source='get_delivery_time_slot_display',
        read_only=True
    )
    time_slot_range = serializers.CharField(
        source='get_time_slot_range',
        read_only=True
    )
    formatted_delivery_time = serializers.CharField(
        source='get_formatted_delivery_time',
        read_only=True
    )
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
    meal_id = serializers.IntegerField(write_only=True, required=False)

    class Meta:
        model = CartItem
        fields = [
            'id', 'custom_meal', 'custom_meal_id', 'custom_meal_details',
            'meals', 'meal_id', 'meal_details',
            'quantity', 'delivery_time_slot', 'delivery_time_slot_display',
            'delivery_time', 'time_slot_range', 'formatted_delivery_time',
            'preferences', 'price_per_item', 'total_price', 'added_at'
        ]
        read_only_fields = ['id', 'added_at']

    def create(self, validated_data):
        custom_meal_id = validated_data.pop('custom_meal_id', None)
        meal_id = validated_data.pop('meal_id', None)

        if custom_meal_id:
            custom_meal = CustomMeal.objects.get(combo_id=custom_meal_id)
            validated_data['custom_meal'] = custom_meal
            # Copy delivery time from custom meal if not provided
            if not validated_data.get('delivery_time_slot') and custom_meal.delivery_time_slot:
                validated_data['delivery_time_slot'] = custom_meal.delivery_time_slot
            if not validated_data.get('delivery_time') and custom_meal.delivery_time:
                validated_data['delivery_time'] = custom_meal.delivery_time

        if meal_id:
            meal = Meals.objects.get(meal_id=meal_id)
            validated_data['meals'] = meal

        return super().create(validated_data)


class ComboCartItemSerializer(serializers.ModelSerializer):
    combo_name = serializers.SerializerMethodField()
    combo_price = serializers.DecimalField(
        source='get_price_per_item',
        max_digits=10,
        decimal_places=2,
        read_only=True
    )
    delivery_time_slot_display = serializers.CharField(
        source='get_delivery_time_slot_display',
        read_only=True
    )
    time_slot_range = serializers.CharField(
        source='get_time_slot_range',
        read_only=True
    )
    formatted_delivery_time = serializers.CharField(
        source='get_formatted_delivery_time',
        read_only=True
    )
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
    
    combo_id = serializers.IntegerField(write_only=True, required=False)
    
    class Meta:
        model = ComboCartItem
        fields = [
            'id', 'combo', 'combo_id', 'combo_name', 'combo_price',
            'quantity', 'subscription_plan', 'delivery_from_date',
            'delivery_to_date', 'delivery_time_slot', 'delivery_time_slot_display',
            'delivery_time', 'time_slot_range', 'formatted_delivery_time',
            'preferences', 'price_per_item', 'total_price', 'added_at'
        ]
        read_only_fields = ['id', 'added_at']
    
    def get_combo_name(self, obj):
        return f"Combo #{obj.combo.cid}"
    
    def create(self, validated_data):
        combo_id = validated_data.pop('combo_id', None)
        
        if combo_id:
            combo = Combo.objects.get(cid=combo_id)
            validated_data['combo'] = combo
        
        return super().create(validated_data)


class CartSerializer(serializers.ModelSerializer):
    cart_items = CartItemSerializer(many=True, read_only=True)
    combo_cart_items = ComboCartItemSerializer(many=True, read_only=True)
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
            'id', 'user', 'cart_items', 'combo_cart_items',
            'subtotal', 'tax', 'delivery_charge', 'total_price', 
            'items_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']