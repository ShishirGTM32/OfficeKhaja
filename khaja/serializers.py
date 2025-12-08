# khaja/serializers.py
from rest_framework import serializers
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
    time_slot_range = serializers.CharField(
        source='get_time_slot_range',
        read_only=True
    )
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

    def validate(self, data):
        """
        Validate that selected meals match the custom meal's category and type
        """
        meal_ids = data.get('meal_ids', [])
        category = data.get('category')
        meal_type = data.get('type')
        
        if not meal_ids:
            raise serializers.ValidationError({
                'meal_ids': 'At least one meal must be selected'
            })
        
        # Fetch the selected meals
        meals = Meals.objects.filter(meal_id__in=meal_ids)
        
        if meals.count() != len(meal_ids):
            raise serializers.ValidationError({
                'meal_ids': 'Some meal IDs are invalid'
            })
        
        # Validate category match
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
        
        # Validate type match
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
        
        return data

    def get_total_price(self, obj):
        return obj.get_total_price()
    
    def get_user_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}"