from rest_framework import serializers
from khaja.models import Meals, Nutrition, CustomMeal, Combo, Ingredients

class IngredientsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredients
        fields = ['iid', 'ingredient_name']


class NutritionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Nutrition
        fields = ['nid', 'energy', 'protein', 'carbs', 'fats', 'sugar']
        read_only_fields = ['nid']


class MealSerializer(serializers.ModelSerializer):
    nutrition = NutritionSerializer(read_only=True)
    ingredients = IngredientsSerializer(many=True, read_only=True)
    
    class Meta:
        model = Meals
        fields = ['meal_id', 'name', 'type', 'description', 'meal_category', 
                  'price', 'image', 'weight', 'nutrition', 'ingredients']
        read_only_fields = ['meal_id']


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

    def create(self, validated_data):
        meal_ids = validated_data.pop("meal_ids")
        meals = Meals.objects.filter(meal_id__in=meal_ids)
        if meals.count() != len(meal_ids):
            raise serializers.ValidationError("Some meal IDs are invalid")
        combo = Combo.objects.create()
        combo.meals.set(meals)
        custom_meal = CustomMeal.objects.create(
            meals=combo,
            **validated_data
        )

        return custom_meal

    def update(self, instance, validated_data):
        meal_ids = validated_data.pop("meal_ids", None)
        
        if meal_ids:
            meals = Meals.objects.filter(meal_id__in=meal_ids)
            if meals.count() != len(meal_ids):
                raise serializers.ValidationError("Some meal IDs are invalid")
            instance.meals.meals.set(meals)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        return instance