from django.urls import path
from .views import (
    MealListView,
    MealDetailView,
    NutritionView,
    CustomMealListView,
    CustomMealDetailView,
    ComboView
)

app_name = 'khaja'

urlpatterns = [
    path('meals/', MealListView.as_view(), name='meal-list'),
    path('meals/<int:meal_id>/', MealDetailView.as_view(), name='meal-detail'),
    path('meals/<int:meal_id>/nutrition/', NutritionView.as_view(), name='nutrition'),
    path('custom-meals/', CustomMealListView.as_view(), name='custom-meal-list'),
    path('custom-meals/<int:combo_id>/', CustomMealDetailView.as_view(), name='custom-meal-detail'),
    path('combos/<int:combo_id>/', ComboView.as_view(), name='combo-detail'),
]
