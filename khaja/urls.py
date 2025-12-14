from django.urls import path
from .views import (
    MealListView, MealDetailView, MealIngredientsView,
    NutritionView, CustomMealListView, CustomMealDetailView,
    IngredientView
)

urlpatterns = [
    path('ingredients/', IngredientView.as_view(), name='ingredient-list'),
    path('ingredients/<int:pk>/', IngredientView.as_view(), name='ingredient-detail'),
    path('meals/', MealListView.as_view(), name='meal-list'),
    path('meals/<slug:slug>/', MealDetailView.as_view(), name='meal-detail'),
    path('meals/<slug:slug>/ingredients/', MealIngredientsView.as_view(), name='meal-ingredients'),
    path('meals/<slug:slug>/nutrition/', NutritionView.as_view(), name='meal-nutrition'),
    path('custom-meals/', CustomMealListView.as_view(), name='custom-meal-list'),
    path('custom-meals/<int:combo_id>/', CustomMealDetailView.as_view(), name='custom-meal-detail'),
]