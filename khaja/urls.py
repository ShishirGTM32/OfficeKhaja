from django.urls import path
from .views import MealView, NutritionView, ComboMealAPI

urlpatterns = [
    path('meals/', MealView.as_view(), name="meals"),
    path('meals/<int:mealid>/nutrition/', NutritionView.as_view(), name="nutrition"),
    path('combo-meals/', ComboMealAPI.as_view(), name="combo")
]