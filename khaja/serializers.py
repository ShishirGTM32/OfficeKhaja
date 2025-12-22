from rest_framework import serializers
from django.utils import timezone
from datetime import datetime
from .models import (Meals, Nutrition, CustomMeal, Combo, Ingredient, 
                     MealIngredient, Type, MealCategory, DeliveryTimeSlot)


class TypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Type
        fields = ['type_id', 'type_name']


class MealCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = MealCategory
        fields = ['cat_id', 'category']


class DeliveryTimeSlotSerializer(serializers.ModelSerializer):
    time_range = serializers.CharField(source='get_time_range', read_only=True)
    
    class Meta:
        model = DeliveryTimeSlot
        fields = ['slot_id', 'name', 'display_name', 'start_time', 'end_time', 'time_range', 'is_active', 'order']


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ['id', 'name', 'category']


class MealIngredientSerializer(serializers.ModelSerializer):
    ingredients = serializers.SerializerMethodField()
    ingredient_ids = serializers.ListField(child=serializers.IntegerField(), required=False, write_only=True)

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
    ingredient_ids = serializers.ListField(child=serializers.IntegerField(), write_only=True, required=False)
    type_name = serializers.CharField(source='type.type_name', read_only=True)
    category_name = serializers.CharField(source='meal_category.category', read_only=True)
    
    class Meta:
        model = Meals
        fields = ['meal_id', 'name', 'type', 'type_name', 'description', 'meal_category', 
                  'category_name', 'slug', 'price', 'image', 'weight', 'nutrition', 
                  'ingredients', 'ingredient_ids', 'is_available']
        read_only_fields = ['meal_id', 'slug']

    def get_ingredients(self, obj):
        if hasattr(obj, 'meal_ingredients'):
            ingredients = obj.meal_ingredients.get_ingredients()
            return IngredientSerializer(ingredients, many=True).data
        return []


class ComboSerializer(serializers.ModelSerializer):
    meals = MealSerializer(many=True, read_only=True)
    meal_count = serializers.SerializerMethodField()
    total_price = serializers.SerializerMethodField()
    total_nutrition = serializers.SerializerMethodField()
    total_weight = serializers.SerializerMethodField()

    class Meta:
        model = Combo
        fields = ['cid', 'meals', 'meal_count', 'total_price', 'total_nutrition', 'total_weight']

    def get_meal_count(self, obj):
        return obj.meals.count()

    def get_total_price(self, obj):
        return obj.get_total_price()

    def get_total_nutrition(self, obj):
        return obj.get_total_nutrition()
    
    def get_total_weight(self, obj):
        return sum(meal.weight for meal in obj.meals.all())


class CustomMealListSerializer(serializers.ModelSerializer):
    type_name = serializers.CharField(source='type.type_name', read_only=True)
    category_name = serializers.CharField(source='meal_category.category', read_only=True)
    delivery_slot_name = serializers.CharField(source='delivery_time_slot.display_name', read_only=True)
    meal_count = serializers.SerializerMethodField()
    total_price = serializers.SerializerMethodField()
    formatted_delivery_time = serializers.CharField(source='get_formatted_delivery_time', read_only=True)
    subscription_plan_name = serializers.CharField(source='subscription_plan.name', read_only=True)

    class Meta:
        model = CustomMeal
        fields = ['combo_id', 'type', 'type_name', 'meal_category', 'category_name', 
                  'no_of_servings', 'meal_count', 'total_price', 'delivery_time_slot',
                  'delivery_slot_name', 'formatted_delivery_time', 'subscription_plan_name', 
                  'is_active', 'created_at']

    def get_meal_count(self, obj):
        return obj.meals.meals.count() if obj.meals else 0

    def get_total_price(self, obj):
        return obj.get_total_price()


class CustomMealSerializer(serializers.ModelSerializer):
    meal_ids = serializers.ListField(child=serializers.IntegerField(), write_only=True, required=True)
    meals = ComboSerializer(read_only=True)
    total_price = serializers.SerializerMethodField()
    user_name = serializers.SerializerMethodField()
    type_name = serializers.CharField(source='type.type_name', read_only=True)
    category_name = serializers.CharField(source='meal_category.category', read_only=True)
    delivery_slot = DeliveryTimeSlotSerializer(source='delivery_time_slot', read_only=True)
    formatted_delivery_time = serializers.CharField(source='get_formatted_delivery_time', read_only=True)
    subscription_plan_name = serializers.CharField(source='subscription_plan.name', read_only=True)

    class Meta:
        model = CustomMeal
        fields = ['combo_id', 'user', 'user_name', 'type', 'type_name', 'meal_category', 
                  'category_name', 'no_of_servings', 'preferences', 'delivery_time_slot',
                  'delivery_slot', 'delivery_time', 'formatted_delivery_time', 
                  'delivery_address', 'meal_ids', 'meals', 'total_price', 'is_active', 
                  'created_at', 'subscription_plan', 'subscription_plan_name']
        read_only_fields = ['combo_id', 'user', 'created_at', 'subscription_plan']

    def validate_delivery_time(self, value):
        if value and value < timezone.now():
            raise serializers.ValidationError("Delivery time cannot be in the past")
        return value

    def validate(self, data):
        meal_ids = data.get('meal_ids', [])
        meal_category = data.get('meal_category')
        meal_type = data.get('type')
        delivery_time = data.get('delivery_time')
        delivery_slot = data.get('delivery_time_slot')
        
        if not meal_ids:
            raise serializers.ValidationError({'meal_ids': 'At least one meal must be selected'})
        
        meals = Meals.objects.filter(meal_id__in=meal_ids, is_available=True)
        
        if meals.count() != len(meal_ids):
            raise serializers.ValidationError({'meal_ids': 'Some meal IDs are invalid or unavailable'})
        
        if not meal_category:
            raise serializers.ValidationError({'meal_category': 'Meal category is required'})
        
        if not meal_type:
            raise serializers.ValidationError({'type': 'Meal type is required'})
        
        mismatched_category = meals.exclude(meal_category=meal_category)
        if mismatched_category.exists():
            mismatched_names = ', '.join(mismatched_category.values_list('name', flat=True))
            category_name = MealCategory.objects.get(cat_id=meal_category).category
            raise serializers.ValidationError({
                'meal_ids': f'All meals must be from "{category_name}" category. Invalid meals: {mismatched_names}'
            })
        
        mismatched_type = meals.exclude(type=meal_type)
        if mismatched_type.exists():
            mismatched_names = ', '.join(mismatched_type.values_list('name', flat=True))
            type_name = Type.objects.get(type_id=meal_type).type_name
            raise serializers.ValidationError({
                'meal_ids': f'All meals must be "{type_name}" type. Invalid meals: {mismatched_names}'
            })
        
        if delivery_time and delivery_slot:
            if not delivery_slot.is_active:
                raise serializers.ValidationError({
                    'delivery_time_slot': 'Selected delivery time slot is not available'
                })
            
            if not delivery_slot.is_time_in_slot(delivery_time):
                time_range = delivery_slot.get_time_range()
                raise serializers.ValidationError({
                    'delivery_time': f'Delivery time must be within the slot range: {time_range}'
                })
        
        if delivery_time and not delivery_slot:
            raise serializers.ValidationError({
                'delivery_time_slot': 'Delivery time slot is required when delivery time is provided'
            })
        
        if delivery_slot and not delivery_time:
            raise serializers.ValidationError({
                'delivery_time': 'Delivery time is required when delivery time slot is provided'
            })
        
        delivery_address = data.get('delivery_address', '').strip()
        if not delivery_address:
            raise serializers.ValidationError({
                'delivery_address': 'Delivery address is required'
            })
        
        return data

    def get_total_price(self, obj):
        return obj.get_total_price()
    
    def get_user_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}"