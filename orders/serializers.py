from rest_framework import serializers
from orders.models import Order, OrderItem, ComboOrderItem, Cart, CartItem
from khaja.models import CustomMeal, Meals
from khaja.serializers import CustomMealSerializer, MealSerializer, CustomMealListSerializer, MealListSerializer
from django.utils import timezone


class OrderItemSerializer(serializers.ModelSerializer):
    meal_details = MealSerializer(source='meals', read_only=True)
    total_price = serializers.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        read_only=True, 
        source='get_total_price'
    )

    class Meta:
        model = OrderItem
        fields = [
            'uuid', 'meals', 'meal_details',
            'meal_type', 'meal_category',
            'quantity', 
            'total_price'
        ]


class ComboOrderItemSerializer(serializers.ModelSerializer):
    combo_details = CustomMealSerializer(source='combo', read_only=True)
    total_price = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        read_only=True,
        source='get_total_price'
    )
    
    class Meta:
        model = ComboOrderItem
        fields = [
            'uuid', 'combo', 'combo_details',
            'delivery_from_date', 'delivery_to_date', 'delivery_time_slot',
            'quantity', 'preferences', 'price_snapshot', 
            'total_price'
        ]


class OrderSerializer(serializers.ModelSerializer):
    order_items = OrderItemSerializer(many=True, read_only=True)
    combo_items = ComboOrderItemSerializer(many=True, read_only=True)
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'uuid', 'user', 'user_name', 'created_at', 'updated_at',
            'subtotal', 'tax', 'delivery_charge', 'total_price',
            'status', 'payment_method', 'delivery_address', 
            'order_items', 'combo_items'
        ]
        read_only_fields = [
            'id', 'user', 'created_at', 'updated_at',
            'subtotal', 'tax', 'delivery_charge', 'total_price'
        ]
    
    def get_user_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}" if obj.user else "Guest"



class CartItemSerializer(serializers.ModelSerializer):
    custom_meal_details = CustomMealListSerializer(source='custom_meal', read_only=True)
    meal_details = MealListSerializer(source='meals', read_only=True)
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
            'quantity', 
            'price_per_item', 'total_price', 'added_at'
        ]
        read_only_fields = ['id', 'added_at']

    def validate(self, data):
        custom_meal_id = data.get('custom_meal_id')
        meal_id = data.get('meal_id')
        if not custom_meal_id and not meal_id:
            raise serializers.ValidationError(
                "Either custom_meal_id or meal_id must be provided"
            )
        
        
        if custom_meal_id and meal_id:
            raise serializers.ValidationError(
                "Cannot provide both custom_meal_id and meal_id"
            )
        
        return data

    def create(self, validated_data):
        custom_meal_id = validated_data.pop('custom_meal_id', None)
        meal_id = validated_data.pop('meal_id', None)

        if custom_meal_id:
            custom_meal = CustomMeal.objects.get(combo_id=custom_meal_id)
            validated_data['custom_meal'] = custom_meal

        if meal_id:
            meal = Meals.objects.get(meal_id=meal_id)
            validated_data['meals'] = meal

        return super().create(validated_data)




class CartItemDetialSerializer(serializers.ModelSerializer):
    custom_meal_details = CustomMealSerializer(source='custom_meal', read_only=True)
    meal_details = MealSerializer(source='meals', read_only=True)
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
            'quantity', 
            'price_per_item', 'total_price', 'added_at'
        ]
        read_only_fields = ['id', 'added_at']

    def validate(self, data):
        custom_meal_id = data.get('custom_meal_id')
        meal_id = data.get('meal_id')
        if not custom_meal_id and not meal_id:
            raise serializers.ValidationError(
                "Either custom_meal_id or meal_id must be provided"
            )
        
        
        if custom_meal_id and meal_id:
            raise serializers.ValidationError(
                "Cannot provide both custom_meal_id and meal_id"
            )
        
        return data

    def create(self, validated_data):
        custom_meal_id = validated_data.pop('custom_meal_id', None)
        meal_id = validated_data.pop('meal_id', None)

        if custom_meal_id:
            custom_meal = CustomMeal.objects.get(combo_id=custom_meal_id)
            validated_data['custom_meal'] = custom_meal

        if meal_id:
            meal = Meals.objects.get(meal_id=meal_id)
            validated_data['meals'] = meal

        return super().create(validated_data)


