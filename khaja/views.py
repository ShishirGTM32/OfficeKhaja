from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Meals, CustomMeal, Nutrition, Combo
from .serializers import MealSerializer, CustomMealSerializer, NutritionSerializer, CustomMealSerializer
from rest_framework import status


class MealView(APIView):

    def get(self, request):
        queryset = Meals.objects.all()
        serializer = MealSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def post(self, request):
        serializer = MealSerializer(data = request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class NutritionView(APIView):
    def get(self, request, mealid):
        queryset = Nutrition.objects.filter(meal_id = mealid)
        serializer = NutritionSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def post(self, request, **kwargs):
        id = kwargs.get('mealid')
        nut = Nutrition.objects.filter(meal_id=id)
        meal = Meals.objects.get(meal_id=id)
        if nut:
            return Response("Nutrition already present", status=status.HTTP_400_BAD_REQUEST)
        serializer = NutritionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(meal_id= meal)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    def put(self, request, **kwargs):
        id = kwargs.get('mealid')
        nut = Nutrition.objects.filter(meal_id=id)
        if nut:
            serializer = NutritionSerializer(nut, data = request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save
            return Response(serializer.data, status=status.HTTP_202_ACCEPTED)
        return Response("Invalid meal id", status=status.HTTP_400_BAD_REQUEST)
    

class ComboMealAPI(APIView):
    def get(self, request):
        combo = CustomMeal.objects.all()
        serializer = CustomMealSerializer(combo, many=True)  
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def post(self, request):
        serializer = CustomMealSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
