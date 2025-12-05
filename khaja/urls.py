from django.urls import path
from .views import MealView, NutritionView

urlpatterns = [
    path('meals/', MealView.as_view(), name="meals"),
    path('meals/<int:id>/nutrition/', NutritionView.as_view(), name="Nutrition")
]