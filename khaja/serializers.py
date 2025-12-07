from rest_framework import serializers
from .models import Meals, Nutrition, CustomMeal, Combo, Ingredient, MealIngredient
from django.contrib.auth.models import User


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
    user_name = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = CustomMeal
        fields = [
            'combo_id', 'user', 'user_name', 'type', 'category', 
            'no_of_servings', 'preferences', 'subscription_plan',
            'delivery_time', 'delivery_address', 'meal_ids', 
            'meals', 'total_price', 'is_active', 'created_at'
        ]
        read_only_fields = ['combo_id', 'user', 'created_at']

    def get_total_price(self, obj):
        return obj.get_total_price()