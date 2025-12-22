from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404
from django.http import Http404
from .models import (Meals, CustomMeal, Nutrition, Combo, Ingredient, DeliveryTimeSlot,
                     MealIngredient, Type, MealCategory)
from .pagination import MenuInfiniteScrollPagination, MealsPagination
from users.models import CustomUser, UserSubscription, Subscription
from users.views import check_subscription
from django.utils import timezone
import datetime
from datetime import timedelta
from orders.models import ComboOrderItem
from orders.permissions import IsSubscribedUser, IsStaff
from .serializers import (
    MealSerializer, CustomMealSerializer, CustomMealListSerializer,
    NutritionSerializer, IngredientSerializer, 
    MealIngredientSerializer, TypeSerializer, MealCategorySerializer, DeliveryTimeSlotSerializer
)


class TypeListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        types = Type.objects.all()
        serializer = TypeSerializer(types, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class DeliveryTimeSlotListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        days_ahead = int(request.GET.get('days', 7))
        today = timezone.localdate()
        slots = DeliveryTimeSlot.objects.filter(is_active=True).order_by('start_time')

        combined_slots = []
        for day_offset in range(days_ahead):
            date = today + timedelta(days=day_offset)
            for slot in slots:
                if date == today and slot.end_time <= timezone.now().time():
                    continue

                combined_slots.append({
                    "id": f"{date}_{slot.slot_id}", 
                    "delivery_date": str(date),
                    "slot_id": slot.slot_id,
                    "display": f"{date.strftime('%d %b')} ({slot.start_time.strftime('%H:%M')} - {slot.end_time.strftime('%H:%M')})"
                })

        return Response(combined_slots, status=status.HTTP_200_OK)

class MealCategoryListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        categories = MealCategory.objects.all()
        serializer = MealCategorySerializer(categories, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


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
            queryset = queryset.filter(meal_category__cat_id=category)
        if meal_type:
            if meal_type.upper() != 'BOTH':
                queryset = queryset.filter(type__type_id=meal_type)
        
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


class CustomMealCreateView(APIView):
    permission_classes = [IsAuthenticated, IsSubscribedUser]

    def get(self, request):
        step = request.query_params.get('step', '1')
        
        if step == '1':
            types = Type.objects.all()
            categories = MealCategory.objects.all()
            return Response({
                'step': 1,
                'title': 'Set your meal preferences',
                'types': TypeSerializer(types, many=True).data,
                'categories': MealCategorySerializer(categories, many=True).data
            }, status=status.HTTP_200_OK)
        
        elif step == '2':
            type_id = request.session['type']
            category_id = request.session['category']
            
            if not type_id or not category_id:
                return Response({'error': 'Type and category are required'}, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                meal_type = Type.objects.get(type_id=type_id)
                category = MealCategory.objects.get(cat_id=category_id)
            except (Type.DoesNotExist, MealCategory.DoesNotExist):
                return Response({'error': 'Invalid type or category'}, status=status.HTTP_400_BAD_REQUEST)
            
            meals = Meals.objects.filter(
                type_id=type_id,
                meal_category_id=category_id,
                is_available=True
            ).select_related('type', 'meal_category', 'nutrition')
            
            if not meals.exists():
                return Response({
                    'step': 2,
                    'title': 'Which items do you want to add to meal?',
                    'message': f'No {meal_type.type_name} meals available for {category.category}',
                    'meals': [],
                    'selected_type': type_id,
                    'selected_category': category_id
                }, status=status.HTTP_200_OK)
            
            return Response({
                'step': 2,
                'title': 'Which items do you want to add to meal?',
                'meals': MealSerializer(meals, many=True).data,
                'selected_type': type_id,
                'selected_type_name': meal_type.type_name,
                'selected_category': category_id,
                'selected_category_name': category.category,
                'total_available': meals.count()
            }, status=status.HTTP_200_OK)
        
        elif step == '3':
            subscriptions = UserSubscription.objects.filter(user=request.user)
            delivery_slots = DeliveryTimeSlot.objects.filter(is_active=True)
            
            subscription_plans = []
            for sub in subscriptions:
                subscription_plans.append({
                    'id': sub.sub_id,
                    'name': sub.plan.subscription,
                    'duration': sub.plan.duration_days,
                    'is_active': True
                })
            
            if not subscription_plans:
                subscription_plans = [{'id': None, 'name': 'No active subscription', 'is_active': False}]
            delivery_address = request.data.get('delivery_address')
            default_address = str(request.user.street_address) if request.user.street_address else delivery_address
            
            return Response({
                'step': 3,
                'title': 'Review delivery details',
                'subtitle': "Let's confirm your meal delivery details",
                'subscription_plans': subscription_plans,
                'delivery_slots': DeliveryTimeSlotSerializer(delivery_slots, many=True).data,
                'delivery_address': default_address,
                'payment_methods': [
                    {'id': 'esewa', 'name': 'E-Sewa'},
                    {'id': 'khalti', 'name': 'Khalti'},
                    {'id': 'cod', 'name': 'Cash on Delivery'}
                ]
            }, status=status.HTTP_200_OK)
        
        return Response({'error': 'Invalid step'}, status=status.HTTP_400_BAD_REQUEST)

    def post(self, request):
        if check_subscription(request.user):
            return Response({'error': 'Subscription not renewed'}, status=status.HTTP_403_FORBIDDEN)
        
        step = request.query_params.get('step', '1')
        
        if step == '1':
            type = request.data.get('type')
            category = request.data.get('category')
            servings = request.data.get('servings')
            preferences = request.data.get('preferences')
            if not type and not category and not servings and not preferences:
                return Response("type, category, servings and preferences field are required", status=status.HTTP_400_BAD_REQUEST)
            if not Type.objects.filter(type_id=type).first():
                return Response("invalid type name. Enter valid type name", status=status.HTTP_404_NOT_FOUND)
            if not MealCategory.objects.filter(cat_id=category).first():
                return Response("invalid category name. Enter valid category name", status=status.HTTP_404_NOT_FOUND)
            request.session['type'] = type
            request.session['category'] = category
            request.session['servings'] = servings
            request.session['preferences'] = preferences
            return Response("Post request success.",status=status.HTTP_200_OK)
        elif step == '2':
            meal_ids = request.data.get('meal_ids')
            meals = Meals.objects.filter(meal_id__in=meal_ids)
            if meals.count() != len(meal_ids):
                return Response("Invalid meal id presented", status=status.HTTP_404_NOT_FOUND)
            request.session['meal_ids'] = meal_ids
            return Response("post request success.",status=status.HTTP_200_OK)
        elif step == '3':
            street_address = request.user.street_address
            delivery_date = request.data.get('delivery_date')
            delivery_address = request.data.get('delivery_address') 
            if not delivery_address:
                delivery_address=street_address
            data = {
                'type':request.session['type'],
                'meal_category':request.session['category'],
                'no_of_servings':request.session['servings'],
                'preferences':request.session['preferences'],
                'meal_ids': request.session['meal_ids'],
                'delivery_address':delivery_address,
                'delivery_date':delivery_date,
                'delivery_time_slot':request.data.get('delivery_time_slot'),
            }
        serializer = CustomMealSerializer(data=data, context={'request': request})
        
        if serializer.is_valid():
            meal_ids = serializer.validated_data.pop('meal_ids')
            meals = Meals.objects.filter(meal_id__in=meal_ids, is_available=True)
            
            if meals.count() != len(meal_ids):
                return Response({'error': 'Some meal IDs are invalid or unavailable'}, status=status.HTTP_400_BAD_REQUEST)
            
            combo = Combo.objects.create()
            combo.meals.set(meals)
            
            subscription = UserSubscription.objects.filter(user=request.user).first()
            sub = Subscription.objects.get(sid=subscription.plan.sid)
            print(sub.sid)
            custom_meal = CustomMeal.objects.create(
                user=request.user,
                meals=combo,
                subscription_plan=subscription,
                **serializer.validated_data
            )
            
            response_data = CustomMealSerializer(custom_meal).data
            response_data['message'] = 'Custom meal created successfully'
            
            return Response(response_data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DeliveryTimeFormatter(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        delivery_time = request.data.get('delivery_time')
        slot_id = request.data.get('delivery_time_slot')
        
        if not delivery_time or not slot_id:
            return Response({'error': 'Both delivery_time and delivery_time_slot are required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            slot = DeliveryTimeSlot.objects.get(slot_id=slot_id, is_active=True)
            from datetime import datetime
            
            if isinstance(delivery_time, str):
                dt = datetime.fromisoformat(delivery_time.replace('Z', '+00:00'))
            else:
                dt = delivery_time
            
            date_str = dt.strftime('%d %b %Y')
            time_str = f"{slot.start_time.strftime('%I:%M %p')} - {slot.end_time.strftime('%I:%M %p')}"
            formatted = f"{date_str}, ({time_str})"
            
            return Response({
                'formatted_delivery_time': formatted,
                'slot_name': slot.display_name,
                'date': date_str,
                'time_range': time_str
            }, status=status.HTTP_200_OK)
            
        except DeliveryTimeSlot.DoesNotExist:
            return Response({'error': 'Invalid delivery slot'}, status=status.HTTP_404_NOT_FOUND)


class CustomMealListView(APIView):
    def get_permissions(self):
        if self.request.method in ['GET', 'POST']:
            permission_classes = [IsAuthenticated, IsSubscribedUser]
        else:
            permission_classes = [IsStaff]
        return [permission() for permission in permission_classes]

    def get(self, request):
        custom_meals = CustomMeal.objects.filter(user=request.user, is_active=True)
        paginator = MenuInfiniteScrollPagination()
        queryset = paginator.paginate_queryset(custom_meals, request=request)
        serializer = CustomMealListSerializer(queryset, many=True)
        return paginator.get_paginated_response(serializer.data)
    
    def post(self, request):
        if check_subscription(request.user):
            return Response({"error": "Subscription not renewed"}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = CustomMealSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            meal_ids = serializer.validated_data.pop('meal_ids')
            meals = Meals.objects.filter(meal_id__in=meal_ids, is_available=True)
            
            if meals.count() != len(meal_ids):
                return Response({"error": "Some meal IDs are invalid or unavailable"}, status=status.HTTP_400_BAD_REQUEST)
            
            combo = Combo.objects.create()
            combo.meals.set(meals)
            
            subscription = UserSubscription.objects.filter(user=request.user).first()
            
            custom_meal = CustomMeal.objects.create(
                user=request.user,
                meals=combo,
                delivery_address=str(request.user.street_address),
                subscription_plan=subscription.plan.subscription if subscription else None,
                **serializer.validated_data
            )
            
            response_serializer = CustomMealSerializer(custom_meal)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CustomMealDetailView(APIView):
    def get_permissions(self):
        if self.request.method in ['GET', 'PUT', 'DELETE']:
            permission_classes = [IsAuthenticated, IsSubscribedUser]
        else:
            permission_classes = [IsStaff]
        return [permission() for permission in permission_classes]

    def get(self, request, combo_id):
        custom_meal = CustomMeal.objects.filter(public_id=combo_id, user=request.user).first()
        if not custom_meal:
            return Response({"error": "Custom meal not found"}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = CustomMealSerializer(custom_meal)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, combo_id):
        try:
            custom_meal = get_object_or_404(CustomMeal, public_id=combo_id, user=request.user)
        except Http404:
            return Response({"error": "Custom meal not found"}, status=status.HTTP_404_NOT_FOUND)
        
        in_order = ComboOrderItem.objects.filter(
            combo_id=custom_meal.combo_id,
            order__status__in=['PENDING', 'PROCESSING', 'DELIVERING']
        ).exists()
        
        if in_order:
            return Response({"error": "Cannot edit custom meal that is in an active order"}, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = CustomMealSerializer(custom_meal, data=request.data, partial=True, context={'request': request})

        if serializer.is_valid():
            meal_ids = serializer.validated_data.pop('meal_ids', None)

            if meal_ids:
                meals = Meals.objects.filter(meal_id__in=meal_ids, is_available=True)
                if meals.count() != len(meal_ids):
                    return Response({"error": "Some meal IDs are invalid or unavailable"}, status=status.HTTP_400_BAD_REQUEST)
                custom_meal.meals.meals.set(meals)

            for attr, value in serializer.validated_data.items():
                setattr(custom_meal, attr, value)
            custom_meal.save()

            response_serializer = CustomMealSerializer(custom_meal)
            return Response(response_serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, combo_id):
        try:
            custom_meal = get_object_or_404(CustomMeal, combo_id=combo_id, user=request.user)
        except Http404:
            return Response({"error": "Custom meal not found"}, status=status.HTTP_404_NOT_FOUND)
        
        in_order = ComboOrderItem.objects.filter(
            combo_id=custom_meal.combo_id,
            order__status__in=['PENDING', 'PROCESSING', 'DELIVERING']
        ).exists()
        
        if in_order:
            return Response({"error": "Cannot delete custom meal that is in an active order"}, status=status.HTTP_400_BAD_REQUEST)
        
        custom_meal.delete()
        return Response({"message": "Custom meal deleted successfully"}, status=status.HTTP_204_NO_CONTENT)