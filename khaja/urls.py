from django.urls import path
from .views import (
    MealListView, MealDetailView, MealIngredientsView,
    NutritionView, CustomMealListView, CustomMealDetailView,
    IngredientView, TypeListView, MealCategoryListView,
    DeliveryTimeSlotListView, CustomMealCreateView
)

app_name = 'khaja'

urlpatterns = [
    path('types/', TypeListView.as_view(), name='types'),
    path('categories/', MealCategoryListView.as_view(), name='categories'),
    path('delivery-slots/', DeliveryTimeSlotListView.as_view(), name='delivery-slots'),
    path('ingredients/', IngredientView.as_view(), name='ingredients'),
    path('ingredients/<int:pk>/', IngredientView.as_view(), name='ingredient-detail'),
    path('meals/', MealListView.as_view(), name='meals'),
    path('meals/<slug:slug>/', MealDetailView.as_view(), name='meal-detail'),
    path('meals/<slug:slug>/ingredients/', MealIngredientsView.as_view(), name='meal-ingredients'),
    path('meals/<slug:slug>/nutrition/', NutritionView.as_view(), name='meal-nutrition'),
    path('custom-meals/', CustomMealListView.as_view(), name='my-custom-meals'),
    path('custom-meals/<uuid:combo_id>/', CustomMealDetailView.as_view(), name='my-custom-meal-detail'),
    path('create-meal/', CustomMealCreateView.as_view(), name='create-custom-meal'),
]