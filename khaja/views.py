from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Meals, CustomMeal, Nutrition
from .serializers import MealSerializer, CustomMealSerializer, NutritionSerializer
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
    def get(self, request, id):
        queryset = Nutrition.objects.filter(meal_id = id)
        serializer = NutritionSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def post(self, request, id):
        nut = Nutrition.objects.filter(meal_id=id)
        meal = meal.object.filter(meal_id=id)
        print(meal)
        if nut:
            return Response("Nutrition already present", status=status.HTTP_400_BAD_REQUEST)
        serializer = NutritionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(meal_id = id)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

