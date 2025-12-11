# khaja/serializers.py
from rest_framework import serializers
from django.utils import timezone
from datetime import datetime
from .models import Meals, Nutrition, CustomMeal, Combo, Ingredient, MealIngredient


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ['id', 'name', 'category']


class MealIngredientSerializer(serializers.ModelSerializer):
    ingredients = serializers.SerializerMethodField()
    ingredient_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        write_only=True
    )

    class Meta:
        model = MealIngredient
        fields = ['meal', 'ingredient_ids', 'ingredients']

    def get_ingredients(self, obj):
        ingredients = obj.get_ingredients()
        return IngredientSerializer(ingredients, many=True).data


class NutritionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Nutrition
        fields = ['nid', 'energy', 'protein', 'carbs', 'fats', 'sugar']
        read_only_fields = ['nid']


class MealSerializer(serializers.ModelSerializer):
    nutrition = NutritionSerializer(read_only=True)
    ingredients = serializers.SerializerMethodField()
    ingredient_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False
    )
    
    class Meta:
        model = Meals
        fields = ['meal_id', 'name', 'type', 'description', 'meal_category', 
                  'price', 'image', 'weight', 'nutrition', 'ingredients', 'ingredient_ids']
        read_only_fields = ['meal_id']

    def get_ingredients(self, obj):
        if hasattr(obj, 'meal_ingredients'):
            ingredients = obj.meal_ingredients.get_ingredients()
            return IngredientSerializer(ingredients, many=True).data
        return []   


class ComboSerializer(serializers.ModelSerializer):
    meals = MealSerializer(many=True, read_only=True)
    total_price = serializers.SerializerMethodField()
    total_nutrition = serializers.SerializerMethodField()

    class Meta:
        model = Combo
        fields = ['cid', 'meals', 'total_price', 'total_nutrition']

    def get_total_price(self, obj):
        return obj.get_total_price()

    def get_total_nutrition(self, obj):
        return obj.get_total_nutrition()


class CustomMealSerializer(serializers.ModelSerializer):
    meal_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=True
    )
    meals = ComboSerializer(read_only=True)
    total_price = serializers.SerializerMethodField()
    user_name = serializers.SerializerMethodField()
    delivery_time_slot_display = serializers.CharField(
        source='get_delivery_time_slot_display',
        read_only=True
    )
    time_slot_range = serializers.SerializerMethodField()
    formatted_delivery_time = serializers.CharField(
        source='get_formatted_delivery_time',
        read_only=True
    )

    class Meta:
        model = CustomMeal
        fields = [
            'combo_id', 'user', 'user_name', 'type', 'category', 
            'no_of_servings', 'preferences', 'delivery_time_slot',
            'delivery_time_slot_display', 'time_slot_range',
            'delivery_time', 'formatted_delivery_time',
            'delivery_address', 'meal_ids', 'meals', 'total_price', 
            'is_active', 'created_at'
        ]
        read_only_fields = ['combo_id', 'user', 'created_at', 'delivery_address']

    def get_time_slot_range(self, obj):
        if obj.delivery_time_slot:
            start, end = CustomMeal.TIME_SLOT_RANGES.get(
                obj.delivery_time_slot, 
                ("00:00", "00:00")
            )
            return f"{start} - {end}"
        return ""

    def validate_delivery_time(self, value):
        if value and value < timezone.now():
            raise serializers.ValidationError(
                "Delivery time cannot be in the past"
            )
        return value

    def validate(self, data):
        meal_ids = data.get('meal_ids', [])
        category = data.get('category')
        meal_type = data.get('type')      
        delivery_time = data.get('delivery_time')
        delivery_slot = data.get('delivery_time_slot')
        
        if not meal_ids:
            raise serializers.ValidationError({
                'meal_ids': 'At least one meal must be selected'
            })
        
        meals = Meals.objects.filter(meal_id__in=meal_ids)
        
        if meals.count() != len(meal_ids):
            raise serializers.ValidationError({
                'meal_ids': 'Some meal IDs are invalid'
            })
        
        if category:
            mismatched_category = meals.exclude(meal_category=category)
            if mismatched_category.exists():
                mismatched_names = ', '.join(
                    mismatched_category.values_list('name', flat=True)
                )
                raise serializers.ValidationError({
                    'meal_ids': f'The following meals do not match the selected category '
                               f'({category}): {mismatched_names}'
                })
        
        if meal_type and meal_type != 'BOTH':
            mismatched_type = meals.exclude(type=meal_type)
            if mismatched_type.exists():
                mismatched_names = ', '.join(
                    mismatched_type.values_list('name', flat=True)
                )
                raise serializers.ValidationError({
                    'meal_ids': f'The following meals do not match the selected type '
                               f'({meal_type}): {mismatched_names}'
                })
        if delivery_time and delivery_slot:
            time_only = delivery_time.time()
            start_str, end_str = CustomMeal.TIME_SLOT_RANGES.get(
                delivery_slot, 
                ("00:00", "23:59")
            )
            
            start_time = datetime.strptime(start_str, '%H:%M').time()
            end_time = datetime.strptime(end_str, '%H:%M').time()
            
            if not (start_time <= time_only <= end_time):
                raise serializers.ValidationError({
                    'delivery_time': f'Delivery time must be between {start_str} and {end_str} '
                                   f'for the selected time slot ({delivery_slot})'
                })
        if delivery_time and not delivery_slot:
            raise serializers.ValidationError({
                'delivery_time_slot': 'Delivery time slot is required when delivery time is provided'
            })
        
        if delivery_slot and not delivery_time:
            raise serializers.ValidationError({
                'delivery_time': 'Delivery time is required when delivery time slot is provided'
            })
        
        return data

    def get_total_price(self, obj):
        return obj.get_total_price()
    
    def get_user_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}"