from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404
from django.http import Http404
from django.db import transaction
from .models import (Meals, CustomMeal, Combo, Ingredient, DeliveryTimeSlot,
                     MealIngredient, Type, MealCategory)
from .pagination import MenuInfiniteScrollPagination, MealsPagination
from users.models import CustomUser, UserSubscription, Subscription
from users.views import check_subscription
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from django.core.cache import cache
from datetime import timedelta, datetime
from orders.models import ComboOrderItem
from orders.permissions import IsSubscribedUser, IsStaff
from .serializers import (
    MealSerializer, CustomMealSerializer, CustomMealListSerializer,
    NutritionSerializer, IngredientSerializer, DeliveryTimeSlotSerializer,
    MealIngredientSerializer, TypeSerializer, MealCategorySerializer
)

@extend_schema(
    request=TypeSerializer,
    responses={200: TypeSerializer}
)
class TypeListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        types = Type.objects.all()
        serializer = TypeSerializer(types, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

@extend_schema(
    request=DeliveryTimeSlotSerializer,
    responses={200: DeliveryTimeSlotSerializer}
)
class DeliveryTimeSlotListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        date_str = request.query_params.get("date")
        if not date_str:
            return Response({"error": "date query param required"}, status=400)

        try:
            delivery_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return Response({"error": "Invalid date format (YYYY-MM-DD)"}, status=400)

        today = timezone.localdate()
        now_time = timezone.localtime().time()

        slots = DeliveryTimeSlot.objects.filter(is_active=True)

        if delivery_date == today:
            slots = slots.filter(start_time__gt=now_time)

        formatted_date = delivery_date.strftime("%d %b %Y")
        data = [
            {
                "slot_id": slot.slot_id,
                "formatted_label": f"{formatted_date} ({slot.start_time.strftime('%H:%M')} - {slot.end_time.strftime('%H:%M')})",
                "time_range": f"{slot.start_time.strftime('%H:%M')} - {slot.end_time.strftime('%H:%M')}"
            }
            for slot in slots   
        ]

        return Response(data, status=200)


@extend_schema(
    request=MealCategorySerializer,
    responses={200: MealCategorySerializer}
)
class MealCategoryListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        categories = MealCategory.objects.all()
        serializer = MealCategorySerializer(categories, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

@extend_schema(
    request=IngredientSerializer,
    responses={200: IngredientSerializer}
)
class IngredientView(APIView):
    def get_permissions(self):
        if self.request.method in ['GET']:
            permission_classes = [AllowAny]
        else:
            permission_classes = [IsStaff]
        return [permission() for permission in permission_classes]

    def get(self, request, pk=None):
        if pk:
            try:
                ingredient = get_object_or_404(Ingredient, slug=pk)
            except Http404:
                return Response({"error": "Invalid ingredient id"}, status=status.HTTP_404_NOT_FOUND)
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
        try:
            ingredient = get_object_or_404(Ingredient, pk=pk)
        except Http404:
            return Response({"error": "Invalid ingredient"}, status=status.HTTP_404_NOT_FOUND)
        serializer = IngredientSerializer(ingredient, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        try:
            ingredient = get_object_or_404(Ingredient, pk=pk)
        except Http404:
            return Response({"error": "Invalid ingredient"}, status=status.HTTP_404_NOT_FOUND)
        ingredient.delete()
        return Response({"message": "Ingredient deleted successfully"}, status=status.HTTP_204_NO_CONTENT)

@extend_schema(
    request=MealSerializer,
    responses={200: MealSerializer}
)
class MealListView(APIView):
    def get_permissions(self):
        if self.request.method in ['GET']:
            permission_classes = [AllowAny]
        else:
            permission_classes = [IsStaff]
        return [permission() for permission in permission_classes]

    def get(self, request):
        category = request.query_params.get('category', None)
        meal_type = request.query_params.get('type', None)
        
        queryset = Meals.objects.filter(is_available=True)
        
        if category:
            queryset = queryset.filter(meal_category__slug=category)
        if meal_type:
            if meal_type.upper() != 'BOTH':
                queryset = queryset.filter(type__slug=meal_type)
        
        paginator = MealsPagination()
        paginated_qs = paginator.paginate_queryset(queryset, request=request)
        serializer = MealSerializer(paginated_qs, many=True)
         
        return paginator.get_paginated_response(serializer.data)
    
    def post(self, request):
        serializer = MealSerializer(data=request.data)
        if serializer.is_valid():
            ingredient_ids = serializer.validated_data.pop('ingredient_ids', [])
            if ingredient_ids:
                ingredients = Ingredient.objects.filter(id__in=ingredient_ids)
                if ingredients.count() != len(ingredient_ids):
                    return Response({"error": "Some ingredient IDs are invalid"}, status=status.HTTP_400_BAD_REQUEST)
            
            meal = serializer.save()
            
            if ingredient_ids:
                MealIngredient.objects.create(meal=meal, ingredient_ids=ingredient_ids)
            
            response_serializer = MealSerializer(meal)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@extend_schema(
    request=MealSerializer,
    responses={200: MealSerializer}
)
class MealDetailView(APIView):
    def get_permissions(self):
        if self.request.method in ['GET']:
            permission_classes = [AllowAny]
        else:
            permission_classes = [IsStaff]
        return [permission() for permission in permission_classes]

    def get(self, request, slug):
        try:
            meal = get_object_or_404(Meals, slug=slug)
        except Http404:
            return Response({"error": "Meal not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = MealSerializer(meal)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, slug):
        try:
            meal = get_object_or_404(Meals, slug=slug)
        except Http404:
            return Response({"error": "Meal not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = MealSerializer(meal, data=request.data, partial=True)
        
        if serializer.is_valid():
            ingredient_ids = serializer.validated_data.pop('ingredient_ids', None)
            if ingredient_ids is not None:
                ingredients = Ingredient.objects.filter(id__in=ingredient_ids)
                if ingredients.count() != len(ingredient_ids):
                    return Response({"error": "Some ingredient IDs are invalid"}, status=status.HTTP_400_BAD_REQUEST)
            
            meal = serializer.save()
            
            if ingredient_ids is not None:
                meal_ingredient, created = MealIngredient.objects.get_or_create(meal=meal)
                meal_ingredient.ingredient_ids = ingredient_ids
                meal_ingredient.save()
            
            response_serializer = MealSerializer(meal)
            return Response(response_serializer.data, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, slug):
        try:
            meal = get_object_or_404(Meals, slug=slug)
        except Http404:
            return Response({"error": "Meal not found"}, status=status.HTTP_404_NOT_FOUND)
        meal.delete()
        return Response({"message": "Meal deleted successfully"}, status=status.HTTP_204_NO_CONTENT)

@extend_schema(
    request=MealIngredientSerializer,
    responses={200: MealIngredientSerializer}
)
class MealIngredientsView(APIView):
    def get_permissions(self):
        if self.request.method in ['GET']:
            permission_classes = [AllowAny]
        else:
            permission_classes = [IsStaff]
        return [permission() for permission in permission_classes]

    def get(self, request, slug):
        try:
            meal = get_object_or_404(Meals, slug=slug)
        except Http404:
            return Response({"error": "Meal not found"}, status=status.HTTP_404_NOT_FOUND)
        
        if hasattr(meal, 'meal_ingredients'):
            serializer = MealIngredientSerializer(meal.meal_ingredients)
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        return Response({"message": "No ingredients found", "ingredients": []}, status=status.HTTP_200_OK)

    def post(self, request, slug):
        try:
            meal = get_object_or_404(Meals, slug=slug)
        except Http404:
            return Response({"error": "Meal not found"}, status=status.HTTP_404_NOT_FOUND)
        ingredient_ids = request.data.get('ingredient_ids', [])
        
        ingredients = Ingredient.objects.filter(id__in=ingredient_ids)
        if ingredients.count() != len(ingredient_ids):
            return Response({"error": "Some ingredient IDs are invalid"}, status=status.HTTP_400_BAD_REQUEST)
        
        meal_ingredient, created = MealIngredient.objects.get_or_create(meal=meal)
        meal_ingredient.ingredient_ids = ingredient_ids
        meal_ingredient.save()
        
        serializer = MealIngredientSerializer(meal_ingredient)
        return Response(serializer.data, status=status.HTTP_200_OK)

@extend_schema(
    request=NutritionSerializer,
    responses={200: NutritionSerializer}
)
class NutritionView(APIView):
    def get_permissions(self):
        if self.request.method in ['GET']:
            permission_classes = [AllowAny]
        else:
            permission_classes = [IsStaff]
        return [permission() for permission in permission_classes]

    def get(self, request, slug):
        try:
            meal = get_object_or_404(Meals, slug=slug)
        except Http404:
            return Response({"error": "Meal not found"}, status=status.HTTP_404_NOT_FOUND)
        
        if hasattr(meal, 'nutrition'):
            serializer = NutritionSerializer(meal.nutrition)
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        return Response({"message": "Nutrition info not available"}, status=status.HTTP_404_NOT_FOUND)
    
    def post(self, request, slug):
        try:
            meal = get_object_or_404(Meals, slug=slug)
        except Http404:
            return Response({"error": "Meal not found"}, status=status.HTTP_404_NOT_FOUND)
        
        if hasattr(meal, 'nutrition'):
            return Response({"error": "Nutrition already exists for this meal"}, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = NutritionSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(meal_id=meal)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def put(self, request, slug):
        try:
            meal = get_object_or_404(Meals, slug=slug)
        except Http404:
            return Response({"error": "Meal not found"}, status=status.HTTP_404_NOT_FOUND)
        
        if not hasattr(meal, 'nutrition'):
            return Response({"error": "Nutrition info doesn't exist"}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = NutritionSerializer(meal.nutrition, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@extend_schema(
    request=CustomMealSerializer,
    responses={200: CustomMealSerializer}
)
class CustomMealCreateView(APIView):
    permission_classes = [IsAuthenticated, IsSubscribedUser]

    def get(self, request):
        step = request.query_params.get('step', '1')
        if step == '1':
            return Response("Setting up category, type, servings and preferences in the backend", status=status.HTTP_200_OK)

        elif step == '2':
            key = f"user:{request.user.phone_number}:createmeal"
            key_data = cache.get(key)
            if not key_data:
                return Response("Invalid user request", status=status.HTTP_400_BAD_REQUEST)

            type_slug = key_data.get("type_slug")
            category_slug = key_data.get("category_slug")
            if not type_slug or not category_slug:
                return Response({'error': 'Type and category are required'}, status=status.HTTP_400_BAD_REQUEST)

            try:
                meal_type = Type.objects.get(slug=type_slug)
                category = MealCategory.objects.get(slug=category_slug)
            except (Type.DoesNotExist, MealCategory.DoesNotExist):
                return Response({'error': 'Invalid type or category'}, status=status.HTTP_400_BAD_REQUEST)

            if meal_type.slug == "both":
                meals = Meals.objects.filter(meal_category__slug=category_slug, is_available=True)
            else:
                meals = Meals.objects.filter(
                    type__slug=type_slug,
                    meal_category__slug=category_slug,
                    is_available=True
                ).select_related('type', 'meal_category', 'nutrition')

            if not meals.exists():
                return Response({
                    'step': 2,
                    'title': 'Which items do you want to add to meal?',
                    'message': f'No {meal_type.type_name} meals available for {category.category}',
                    'meals': [],
                    'selected_type': type_slug,
                    'selected_category': category_slug
                }, status=status.HTTP_200_OK)

            return Response({
                'step': 2,
                'title': 'Which items do you want to add to meal?',
                'meals': MealSerializer(meals, many=True).data,
                'selected_type': type_slug,
                'selected_type_name': meal_type.type_name,
                'selected_category': category_slug,
                'selected_category_name': category.category,
                'total_available': meals.count()
            }, status=status.HTTP_200_OK)

        elif step == '3':
            subscriptions = UserSubscription.objects.filter(user=request.user)
            delivery_slots = DeliveryTimeSlot.objects.filter(is_active=True)
            subscription_plans = [{'id': sub.sub_id, 'name': sub.plan.subscription, 'duration': sub.plan.duration_days, 'is_active': True} for sub in subscriptions]

            if not subscription_plans:
                subscription_plans = [{'id': None, 'name': 'No active subscription', 'is_active': False}]

            delivery_address = request.data.get('delivery_address') or str(request.user.street_address)

            return Response({
                'step': 3,
                'title': 'Review delivery details',
                'subtitle': "Let's confirm your meal delivery details",
                'delivery_slots': DeliveryTimeSlotSerializer(delivery_slots, many=True).data,
                'delivery_address': delivery_address,   
                'payment_methods': request.user.payment_method
            }, status=status.HTTP_200_OK)

        return Response({'error': 'Invalid step'}, status=status.HTTP_400_BAD_REQUEST)


    def post(self, request):
        if check_subscription(request.user):
            return Response(
                {"error": "Subscription not renewed"},
                status=status.HTTP_403_FORBIDDEN
            )

        if request.query_params.get("step") != "3":
            return Response(
                {"error": "Invalid step"},
                status=status.HTTP_400_BAD_REQUEST
            )

        key = f"user:{request.user.phone_number}:createmeal"
        key_data = cache.get(key)
        if not key_data:
            return Response(
                {"error": "Session expired"},
                status=status.HTTP_400_BAD_REQUEST
            )

        delivery_date_str = request.data.get("delivery_date")
        delivery_time_slot_id = request.data.get("delivery_time_slot")

        if not delivery_date_str or not delivery_time_slot_id:
            return Response(
                {"error": "Delivery date and time slot are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            delivery_date = datetime.strptime(
                delivery_date_str, "%Y-%m-%d"
            ).date()
        except ValueError:
            return Response(
                {"error": "Invalid delivery date format (YYYY-MM-DD)"},
                status=status.HTTP_400_BAD_REQUEST
            )


        delivery_slot = get_object_or_404(
            DeliveryTimeSlot,
            slot_id=delivery_time_slot_id,
            is_active=True
        )

        today = timezone.localdate()
        now_time = timezone.localtime().time()

        if delivery_date == today:
            if delivery_slot.start_time <= now_time:
                return Response(
                    {"error": "Selected time slot has already passed"},
                    status=status.HTTP_400_BAD_REQUEST
                )

        data = {
            "type_slug": key_data["type_slug"],
            "meal_category_slug": key_data["category_slug"],
            "no_of_servings": key_data["servings"],
            "preferences": key_data["preferences"],
            "meal_ids": key_data["meal_ids"],
            "delivery_address": request.data.get("delivery_address")
                or request.user.street_address,
            "delivery_date": delivery_date,
            "delivery_time_slot": delivery_slot.slot_id
        }

        serializer = CustomMealSerializer(
            data=data,
            context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        meals = Meals.objects.filter(
            meal_id__in=serializer.validated_data.pop("meal_ids"),
            is_available=True
        )

        combo = Combo.objects.create()
        combo.meals.set(meals)

        subscription = UserSubscription.objects.filter(
            user=request.user
        ).first()

        custom_meal = CustomMeal.objects.create(
            user=request.user,
            meals=combo,
            subscription_plan=subscription,
            **serializer.validated_data
        )

        cache.delete(key)

        return Response(
            CustomMealSerializer(custom_meal).data,
            status=status.HTTP_201_CREATED
        )

    def patch(self, request):   
        if check_subscription(request.user):
            return Response(
                {"error": "Subscription not renewed"},
                status=status.HTTP_403_FORBIDDEN
            )

        step = request.query_params.get("step")
        key = f"user:{request.user.phone_number}:createmeal"
        if step == "1":
            cache.delete(key)
            type_slug = request.data.get("type")
            category_slug = request.data.get("category")

            if not Type.objects.filter(slug=type_slug).exists():
                return Response(
                    {"error": "Invalid type"},
                    status=status.HTTP_404_NOT_FOUND
                )

            if not MealCategory.objects.filter(slug=category_slug).exists():
                return Response(
                    {"error": "Invalid category"},
                    status=status.HTTP_404_NOT_FOUND
                )

            cache.set(
                key,
                {
                    "type_slug": type_slug,
                    "category_slug": category_slug,
                    "servings": request.data.get("servings"),
                    "preferences": request.data.get("preferences")
                },
                timeout=600
            )
            return Response({"success": True}, status=status.HTTP_200_OK)

        elif step == "2":
            meal_ids = request.data.get("meal_ids", [])
            meals = Meals.objects.filter(meal_id__in=meal_ids)

            if meals.count() != len(meal_ids):
                return Response(
                    {"error": "Invalid meal selection"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            key_data = cache.get(key)
            if not key_data:
                return Response(
                    {"error": "Session expired"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            key_data["meal_ids"] = meal_ids
            cache.set(key, key_data, timeout=600)

            return Response({"success": True}, status=status.HTTP_200_OK)

        return Response(
            {"error": "Invalid step"},
            status=status.HTTP_400_BAD_REQUEST
        )


@extend_schema(
    request=CustomMealSerializer,
    responses={200: CustomMealSerializer}
)
class CustomMealListView(APIView):
    def get_permissions(self):
        if self.request.method in ['GET']:
            permission_classes = [IsAuthenticated, IsSubscribedUser]
        else:
            permission_classes = [IsStaff]
        return [permission() for permission in permission_classes]

    def get(self, request):
        custom_meals = CustomMeal.objects.filter(user=request.user, is_active=True)
        type = request.query_params.get('type', None)
        category = request.query_params.get('category',None)
        if type:
            custom_meals=custom_meals.filter(type__slug=type)
        if category:
            custom_meals=custom_meals.filter(category__slug=category)
        paginator = MenuInfiniteScrollPagination()
        queryset = paginator.paginate_queryset(custom_meals, request=request)
        serializer = CustomMealListSerializer(queryset, many=True)
        return paginator.get_paginated_response(serializer.data)

@extend_schema(
    request=CustomMealSerializer,
    responses={200: CustomMealSerializer}
)
class CustomMealDetailView(APIView):
    def get_permissions(self):
        if self.request.method in ['GET', 'PATCH', 'DELETE']:
            permission_classes = [IsAuthenticated, IsSubscribedUser]
        else:
            permission_classes = [IsStaff]
        return [permission() for permission in permission_classes]

    def get(self, request, combo_id):
        custom_meal = CustomMeal.objects.filter(public_id=combo_id, user=request.user).first()
        if not custom_meal:
            return Response({"error": "Custom meal not found or doesnot belongs to you."}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = CustomMealSerializer(custom_meal)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def patch(self, request, combo_id):
        custom_meal = get_object_or_404(CustomMeal, public_id=combo_id, user=request.user)
        in_order = ComboOrderItem.objects.filter(
            combo_id=custom_meal.combo_id,
            order__status__in=['PENDING', 'PROCESSING', 'DELIVERING']
        ).exists()

        if in_order:
            return Response(
                {"error": "Cannot edit custom meal that is in an active order"},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = CustomMealSerializer(
            custom_meal, 
            data=request.data, 
            partial=True, 
            context={'request': request}
        )

        with transaction.atomic():
            if serializer.is_valid():
                meal_ids = serializer.validated_data.pop('meal_ids', None)
                if meal_ids is not None:
                    meals = Meals.objects.filter(meal_id__in=meal_ids, is_available=True)
                    if meals.count() != len(meal_ids):
                        return Response(
                            {"error": "Some meal IDs are invalid or unavailable"},
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
        try:
            custom_meal = get_object_or_404(CustomMeal, public_id=combo_id, user=request.user)
        except Http404:
            return Response({"error": "Custom meal not found"}, status=status.HTTP_404_NOT_FOUND)
        
        in_order = ComboOrderItem.objects.filter(
            combo_id=custom_meal.combo_id,
            order__status__in=['PENDING', 'PROCESSING', 'DELIVERING']
        ).exists()
        
        if in_order:
            return Response({"error": "Cannot delete custom meal that is in an active order"}, status=status.HTTP_400_BAD_REQUEST)
        
        custom_meal.delete()
        return Response({"message": "Custom meal deleted successfully"}, status=status.HTTP_200_OK)

