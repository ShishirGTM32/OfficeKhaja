
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404
from khaja.models import Meals, CustomMeal, Nutrition, Combo
from orders.models import Order, OrderItem, Cart, CartItem
from .serializers import (
    MealSerializer, CustomMealSerializer, NutritionSerializer, ComboSerializer,
    OrderSerializer, OrderCreateSerializer, CartSerializer, CartItemSerializer
)


# ===================== KHAJA VIEWS =====================

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
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
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
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, meal_id):
        meal = get_object_or_404(Meals, meal_id=meal_id)
        meal.delete()
        return Response(
            {"message": "Meal deleted successfully"}, 
            status=status.HTTP_204_NO_CONTENT
        )


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

    permission_classes = [AllowAny]

    def get(self, request):
        custom_meals = CustomMeal.objects.filter(user=request.user, is_active=True)
        serializer = CustomMealSerializer(custom_meals, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def post(self, request):
        serializer = CustomMealSerializer(
            data=request.data,
            context={'request': request}
        )
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CustomMealDetailView(APIView):
    permission_classes = [AllowAny]

    def get_object(self, combo_id, user):
        return get_object_or_404(CustomMeal, combo_id=combo_id, user=user)

    def get(self, request, combo_id):
        custom_meal = self.get_object(combo_id, request.user)
        serializer = CustomMealSerializer(custom_meal)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, combo_id):
        custom_meal = self.get_object(combo_id, request.user)
        serializer = CustomMealSerializer(
            custom_meal, 
            data=request.data, 
            partial=True,
            context={'request': request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
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