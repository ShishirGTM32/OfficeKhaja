from rest_framework import serializers
from .models import Meals, Nutrition, CustomMeal

class MealSerializer(serializers.ModelSerializer):
    class Meta:
        model = Meals
        fields = ['meal_id', 'name', 'type', 'description', 'meal_category', 'price']
        read_only_fields = ['meal_id']

class NutritionSerializer(serializers.ModelSerializer):
    meals = MealSerializer(read_only = True)
    class Meta:
        model = Nutrition
        fields = ['nid', 'meal_id', 'meals', 'energy', 'protien', 'carbs', 'fats', 'sugar']
        read_only_fields = ['nid', 'meals', "meal_id"]
    
class CustomMealSerializer(serializers.ModelSerializer):
    meals = MealSerializer(read_only=True)
    class Meta:
        fields = ['combo_id', 'meals', 'no_of_servings', 'preferences'  'delivery_time']
        read_only_field = ['combo_id']