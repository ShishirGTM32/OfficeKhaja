from rest_framework import serializers
from django.utils import timezone
from datetime import datetime
from .models import (Meals, Nutrition, CustomMeal, Combo, Ingredient, 
                     MealIngredient, Type, MealCategory, DeliveryTimeSlot)


class TypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Type
        fields = ['type_id', 'type_name', 'slug']


class MealCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = MealCategory
        fields = ['cat_id', 'category', 'slug']


class DeliveryTimeSlotSerializer(serializers.ModelSerializer):
    time_range = serializers.CharField(source='get_time_range', read_only=True)
    
    class Meta:
        model = DeliveryTimeSlot
        fields = ['slot_id', 'name', 'display_name', 'start_time', 'end_time', 'time_range', 'is_active', 'slug']


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


class MealListSerializer(serializers.ModelSerializer):
    nutrition = NutritionSerializer(read_only=True)
    
    class Meta:
        model = Meals
        fields = ['meal_id', 'name', 'description','slug', 'price', 'image', 'weight', 'nutrition', 'is_available']
        read_only_fields = ['meal_id', 'slug']


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
    meals = MealListSerializer(many=True, read_only=True)
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
    subscription_plan_name = serializers.CharField(source='subscription_plan.plan.subscription', read_only=True)

    class Meta:
        model = CustomMeal
        fields = ['combo_id','public_id', 'type', 'type_name', 'meal_category', 'category_name', 
                  'no_of_servings', 'meal_count', 'total_price', 'delivery_time_slot',
                  'delivery_slot_name', 'formatted_delivery_time', 'subscription_plan_name', 
                  'is_active', 'created_at']

    def get_meal_count(self, obj):
        return obj.meals.meals.count() if obj.meals else 0

    def get_total_price(self, obj):
        return obj.get_total_price()


class CustomMealSerializer(serializers.ModelSerializer):
    meal_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False
    )

    type_slug = serializers.SlugField(write_only=True, required=False)
    meal_category_slug = serializers.SlugField(write_only=True, required=False)

    meals = ComboSerializer(read_only=True)
    total_price = serializers.SerializerMethodField()
    user_name = serializers.SerializerMethodField()
    type_name = serializers.CharField(source='type.type_name', read_only=True)
    category_name = serializers.CharField(source='meal_category.category', read_only=True)
    delivery_slot = DeliveryTimeSlotSerializer(source='delivery_time_slot', read_only=True)
    formatted_delivery_time = serializers.CharField(source='get_formatted_delivery_time', read_only=True)
    subscription_plan_name = serializers.CharField(source='subscription_plan.plan.subscription', read_only=True)

    class Meta:
        model = CustomMeal
        fields = [
            'combo_id', 'user', 'user_name', 'public_id',
            'type', 'type_slug', 'type_name',
            'meal_category', 'meal_category_slug', 'category_name',
            'no_of_servings', 'preferences',
            'delivery_time_slot', 'delivery_slot', 'delivery_date',
            'formatted_delivery_time', 'delivery_address',
            'meal_ids', 'meals', 'total_price',
            'is_active', 'created_at',
            'subscription_plan', 'subscription_plan_name'
        ]
        read_only_fields = ['combo_id', 'user', 'created_at', 'subscription_plan', 'type', 'meal_category']

    def validate(self, data):
        type_slug = data.pop('type_slug', None)
        category_slug = data.pop('meal_category_slug', None)
        
        if type_slug:
            try:
                data['type'] = Type.objects.get(slug=type_slug)
            except Type.DoesNotExist:
                raise serializers.ValidationError({'type_slug': 'Invalid type'})

        if category_slug:
            try:
                data['meal_category'] = MealCategory.objects.get(slug=category_slug)
            except MealCategory.DoesNotExist:
                raise serializers.ValidationError({'meal_category_slug': 'Invalid category'})

        meal_type = data.get('type') or self.instance.type
        meal_category = data.get('meal_category') or self.instance.meal_category
        meal_ids = data.get('meal_ids')

        if meal_ids:
            meals = Meals.objects.filter(meal_id__in=meal_ids, is_available=True)
            if meals.count() != len(meal_ids):
                raise serializers.ValidationError({'meal_ids': 'Some meal IDs are invalid or unavailable'})

            if meals.exclude(meal_category=meal_category).exists():
                raise serializers.ValidationError({
                    'meal_ids': f'All meals must belong to "{meal_category.category}" category'
                })

            if meal_type.slug != 'both' and meals.exclude(type=meal_type).exists():
                raise serializers.ValidationError({
                    'meal_ids': f'All meals must be "{meal_type.type_name}" type'
                })

        delivery_date = data.get('delivery_date')
        delivery_slot = data.get('delivery_time_slot')

        if delivery_slot and not delivery_date:
            raise serializers.ValidationError({'delivery_date': 'Delivery date is required with delivery slot'})

        if delivery_date and delivery_slot and not delivery_slot.is_active:
            raise serializers.ValidationError({'delivery_time_slot': 'Selected delivery slot is not active'})

        return data

    def get_total_price(self, obj):
        return obj.get_total_price()

    def get_user_name(self, obj):
        if obj.user.user_type == "ORGANIZATIONS":
            return obj.user.organization_name
        return f"{obj.user.first_name} {obj.user.last_name}"

