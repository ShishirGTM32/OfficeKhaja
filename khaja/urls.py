from django.urls import path
from .views import (
    IngredientView,
    MealListView,
    MealDetailView,
    MealIngredientsView,
    NutritionView,
    CustomMealListView,
    CustomMealDetailView,
    ComboView
)

app_name = 'khaja'

urlpatterns = [
    path('ingredients/', IngredientView.as_view(), name='ingredient-list'),
    path('ingredients/<int:pk>/', IngredientView.as_view(), name='ingredient-detail'),

    path('meals/', MealListView.as_view(), name='meal-list'),
    path('meals/<int:meal_id>/', MealDetailView.as_view(), name='meal-detail'),
    path('meals/<int:meal_id>/ingredients/', MealIngredientsView.as_view(), name='meal-ingredients'),
    path('meals/<int:meal_id>/nutrition/', NutritionView.as_view(), name='nutrition'),

    path('custom-meals/', CustomMealListView.as_view(), name='custom-meal-list'),
    path('custom-meals/<int:combo_id>/', CustomMealDetailView.as_view(), name='custom-meal-detail'),

    path('combos/<int:combo_id>/', ComboView.as_view(), name='combo-detail'),
]