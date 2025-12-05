from rest_framework import serializers
from .models import Meals, Nutrition, CustomMeal, Combo

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
    meal_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True
    )

    class Meta:
        model = CustomMeal
        fields = [
            "combo_id",
            "user",
            "type",
            "category",
            "no_of_consumer",
            "preferences",
            "meal_ids"     
        ]

    def create(self, validated_data):
        meal_ids = validated_data.pop("meal_ids")
        combo = Combo.objects.create()
        combo.meals.set(meal_ids)
        custom_meal = CustomMeal.objects.create(
            meals=combo,
            **validated_data
        )

        return custom_meal

