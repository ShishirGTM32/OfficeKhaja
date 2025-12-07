
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404
from khaja.models import Meals, CustomMeal, Nutrition, Combo, Ingredient, MealIngredient
from .serializers import (
    MealSerializer, CustomMealSerializer, NutritionSerializer, ComboSerializer,
    IngredientSerializer, MealIngredientSerializer
)

class IngredientView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, pk=None):
        if pk:
            ingredient = get_object_or_404(Ingredient, pk=pk)
            serializer = IngredientSerializer(ingredient)
            return Response(serializer.data, status=status.HTTP_200_OK)

        category = request.query_params.get('category', None)
        
        queryset = Ingredient.objects.all()
        
        if category:
            queryset = queryset.filter(category=category)
        
        serializer = IngredientSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def post(self, request):
        serializer = IngredientSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        ingredient = get_object_or_404(Ingredient, pk=pk)
        serializer = IngredientSerializer(ingredient, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        ingredient = get_object_or_404(Ingredient, pk=pk)
        ingredient.delete()
        return Response(
            {"message": "Ingredient deleted successfully"}, 
            status=status.HTTP_204_NO_CONTENT
        )


class MealListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        category = request.query_params.get('category', None)
        meal_type = request.query_params.get('type', None)
        
        queryset = Meals.objects.all()
        
        if category:
            queryset = queryset.filter(meal_category=category.upper())
        if meal_type:
            queryset = queryset.filter(type=meal_type.upper())
        
        serializer = MealSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def post(self, request):
        serializer = MealSerializer(data=request.data)
        if serializer.is_valid():
            ingredient_ids = serializer.validated_data.pop('ingredient_ids', [])
            if ingredient_ids:
                ingredients = Ingredient.objects.filter(id__in=ingredient_ids)
                if ingredients.count() != len(ingredient_ids):
                    return Response(
                        {"error": "Some ingredient IDs are invalid"}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
            meal = serializer.save()
            
            if ingredient_ids:
                MealIngredient.objects.create(
                    meal=meal,
                    ingredient_ids=ingredient_ids
                )
            
            response_serializer = MealSerializer(meal)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MealDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, meal_id):
        meal = get_object_or_404(Meals, meal_id=meal_id)
        serializer = MealSerializer(meal)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, meal_id):
        meal = get_object_or_404(Meals, meal_id=meal_id)
        serializer = MealSerializer(meal, data=request.data, partial=True)
        
        if serializer.is_valid():
            # Extract ingredient_ids from validated data
            ingredient_ids = serializer.validated_data.pop('ingredient_ids', None)
            
            # Validate ingredient IDs if provided
            if ingredient_ids is not None:
                ingredients = Ingredient.objects.filter(id__in=ingredient_ids)
                if ingredients.count() != len(ingredient_ids):
                    return Response(
                        {"error": "Some ingredient IDs are invalid"}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
            meal = serializer.save()
        
            if ingredient_ids is not None:
                meal_ingredient, created = MealIngredient.objects.get_or_create(meal=meal)
                meal_ingredient.ingredient_ids = ingredient_ids
                meal_ingredient.save()
            
            response_serializer = MealSerializer(meal)
            return Response(response_serializer.data, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, meal_id):
        meal = get_object_or_404(Meals, meal_id=meal_id)
        meal.delete()
        return Response(
            {"message": "Meal deleted successfully"}, 
            status=status.HTTP_204_NO_CONTENT
        )


class MealIngredientsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, meal_id):
        meal = get_object_or_404(Meals, meal_id=meal_id)
        
        if hasattr(meal, 'meal_ingredients'):
            serializer = MealIngredientSerializer(meal.meal_ingredients)
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        return Response(
            {"message": "No ingredients found", "ingredients": []}, 
            status=status.HTTP_200_OK
        )

    def post(self, request, meal_id):
        meal = get_object_or_404(Meals, meal_id=meal_id)
        ingredient_ids = request.data.get('ingredient_ids', [])
        
        ingredients = Ingredient.objects.filter(id__in=ingredient_ids)
        if ingredients.count() != len(ingredient_ids):
            return Response(
                {"error": "Some ingredient IDs are invalid"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        meal_ingredient, created = MealIngredient.objects.get_or_create(meal=meal)
        meal_ingredient.ingredient_ids = ingredient_ids
        meal_ingredient.save()
        
        serializer = MealIngredientSerializer(meal_ingredient)
        return Response(serializer.data, status=status.HTTP_200_OK)


class NutritionView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, meal_id):
        meal = get_object_or_404(Meals, meal_id=meal_id)
        
        if hasattr(meal, 'nutrition'):
            serializer = NutritionSerializer(meal.nutrition)
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        return Response(
            {"message": "Nutrition info not available"}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    def post(self, request, meal_id):
        meal = get_object_or_404(Meals, meal_id=meal_id)
        
        if hasattr(meal, 'nutrition'):
            return Response(
                {"error": "Nutrition already exists for this meal"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = NutritionSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(meal_id=meal)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def put(self, request, meal_id):
        meal = get_object_or_404(Meals, meal_id=meal_id)
        
        if not hasattr(meal, 'nutrition'):
            return Response(
                {"error": "Nutrition info doesn't exist"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = NutritionSerializer(
            meal.nutrition, 
            data=request.data, 
            partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CustomMealListView(APIView):
    #need to specify users for the meals and corresponding custom meal to be set
    permission_classes = [AllowAny]

    def get(self, request):
        custom_meals = CustomMeal.objects.filter( is_active=True)
        serializer = CustomMealSerializer(custom_meals, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def post(self, request):
        serializer = CustomMealSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            meal_ids = serializer.validated_data.pop('meal_ids')
            meals = Meals.objects.filter(meal_id__in=meal_ids)
            if meals.count() != len(meal_ids):
                return Response(
                    {"error": "Some meal IDs are invalid"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            combo = Combo.objects.create()
            combo.meals.set(meals)
            custom_meal = CustomMeal.objects.create(
                meals=combo,
                **serializer.validated_data
            )
            response_serializer = CustomMealSerializer(custom_meal)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CustomMealDetailView(APIView):
    #need to specify users for the meals and corresponding custom meal to be set
    permission_classes = [AllowAny]

    def get_object(self, combo_id):
        return get_object_or_404(CustomMeal, combo_id=combo_id)

    def get(self, request, combo_id):
        custom_meal = self.get_object(combo_id)
        serializer = CustomMealSerializer(custom_meal)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, combo_id):
        custom_meal = self.get_object(combo_id)
        serializer = CustomMealSerializer(
            custom_meal, 
            data=request.data, 
            partial=True,
            context={'request': request}
        )
        
        if serializer.is_valid():
            meal_ids = serializer.validated_data.pop('meal_ids', None)
            
            if meal_ids:
                meals = Meals.objects.filter(meal_id__in=meal_ids)
                if meals.count() != len(meal_ids):
                    return Response(
                        {"error": "Some meal IDs are invalid"}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
                custom_meal.meals.meals.set(meals)
            for attr, value in serializer.validated_data.items():
                setattr(custom_meal, attr, value)
            custom_meal.save()
            response_serializer = CustomMealSerializer(custom_meal)
            return Response(response_serializer.data, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, combo_id):
        custom_meal = self.get_object(combo_id, request.user)
        custom_meal.is_active = False
        custom_meal.save()
        return Response(
            {"message": "Custom meal deleted"}, 
            status=status.HTTP_204_NO_CONTENT
        )


class ComboView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, combo_id):
        combo = get_object_or_404(Combo, cid=combo_id)
        serializer = ComboSerializer(combo)
        return Response(serializer.data, status=status.HTTP_200_OK)
