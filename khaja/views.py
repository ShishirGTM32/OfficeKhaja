from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404
from django.utils import timezone
from .models import Meals, CustomMeal, Nutrition, Combo, Ingredient, MealIngredient
from .pagination import MenuInfiniteScrollPagination
from users.models import CustomUser, UserSubscription
from orders.models import ComboOrderItem
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
        category = request.query_params.get('   ', None)
        meal_type = request.query_params.get('type', None)
        
        queryset = Meals.objects.all()
        
        if category:
            queryset = queryset.filter(meal_category=category)
        if meal_type:
            if meal_type.upper() != 'BOTH':
                queryset = queryset.filter(type=meal_type.upper())
        pagiantor = MenuInfiniteScrollPagination()
        qs = pagiantor.paginate_queryset(queryset, request)
        serializer = MealSerializer(qs, many=True)
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
            ingredient_ids = serializer.validated_data.pop('ingredient_ids', None)
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
        if request.user.is_staff or request.user.is_superuser:
            meal = get_object_or_404(Meals, meal_id=meal_id)
            meal.delete()
            return Response(
                {"message": "Meal deleted successfully"}, 
                status=status.HTTP_204_NO_CONTENT
            )
        else:
            return Response({"message":"Unauthorized access"}, status=status.HTTP_401_UNAUTHORIZED)

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
    permission_classes = [IsAuthenticated]

    def get(self, request):
        custom_meals = CustomMeal.objects.filter(user=request.user, is_active=True)
        paginator = MenuInfiniteScrollPagination()
        queryset = paginator.paginate_queryset(custom_meals, request=True)
        serializer = CustomMealSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def post(self, request):
        try:
            subscription = UserSubscription.objects.get(user=request.user)
            if not subscription.is_active or subscription.expires_on < timezone.now().date():
                return Response(
                    {"error": "Your subscription has expired. Please renew to create custom meals."},
                    status=status.HTTP_403_FORBIDDEN
                )
        except UserSubscription.DoesNotExist:
            return Response(
                {"error": "Please subscribe to a plan first"},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = CustomMealSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            user = CustomUser.objects.get(id=request.user.id)
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
                user=request.user,
                meals=combo,
                delivery_address=str(user.street_address),
                **serializer.validated_data,
                subscription_plan=subscription
            )
            
            response_serializer = CustomMealSerializer(custom_meal)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CustomMealDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, combo_id):
        custom_meal = CustomMeal.objects.filter(
            combo_id=combo_id, 
            user=request.user
        ).first()
        if not custom_meal:
            return Response(
                {"error": "Custom meal not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = CustomMealSerializer(custom_meal)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, combo_id):
        custom_meal = get_object_or_404(
            CustomMeal, 
            combo_id=combo_id, 
            user=request.user
        )
        
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
        custom_meal = get_object_or_404(
            CustomMeal, 
            combo_id=combo_id, 
            user=request.user
        )
        in_order = ComboOrderItem.objects.filter(
            combo_id=custom_meal.combo_id,
            order__status__in=['PENDING', 'PROCESSING', 'DELIVERING']
        ).exists()
        
        if in_order:
            return Response(
                {"error": "Cannot delete custom meal that is in an active order"},
                status=status.HTTP_400_BAD_REQUEST
            )
        custom_meal.delete()
        
        return Response(
            {"message": "Custom meal deleted"}, 
            status=status.HTTP_204_NO_CONTENT
        )