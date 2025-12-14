# orders/admin_views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.core.mail import send_mail
from django.conf import settings
from django.http import Http404
from django.utils import timezone
from django.db.models import Count, Sum, Q
from orders.permissions import IsStaff
from orders.models import Order, OrderItem, ComboOrderItem
from khaja.models import Meals, CustomMeal, Combo, Nutrition, Ingredient, MealIngredient
from users.models import CustomUser, Subscription, UserSubscription
from orders.serializers import OrderSerializer, OrderItemSerializer, ComboOrderItemSerializer
from khaja.serializers import (
    MealSerializer, CustomMealSerializer, NutritionSerializer, 
    ComboSerializer, IngredientSerializer, MealIngredientSerializer
)
from users.serializers import UserSerializer, SubscriptionSerializer, UserSubscriptionSerializer
from khaja.pagination import MenuInfiniteScrollPagination


class AdminUserListView(APIView):
    permission_classes = [IsAuthenticated, IsStaff]

    def get(self, request):
        users = CustomUser.objects.all().order_by('-created_at')
        
        user_type = request.query_params.get('user_type')
        is_active = request.query_params.get('is_active')
        status_filter = request.query_params.get('status')
        
        if user_type:
            users = users.filter(user_type=user_type.upper())
        if is_active is not None:
            users = users.filter(is_active=is_active.lower() == 'true')
        if status_filter is not None:
            users = users.filter(status=status_filter.lower() == 'true')
        
        paginator = MenuInfiniteScrollPagination()
        queryset = paginator.paginate_queryset(users, request)
        serializer = UserSerializer(queryset, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            password = request.data.get('password')
            user = serializer.save()
            if password:
                user.set_password(password)
                user.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class AdminUserDetailView(APIView):
    permission_classes = [IsAuthenticated, IsStaff]

    def get(self, request, user_id):
        try:
            user = get_object_or_404(CustomUser, id=user_id)
        except Http404:
            return Response("Invalid user please check the user id again.", status=status.HTTP_404_NOT_FOUND)
        serializer = UserSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, user_id):
        try:
            user = get_object_or_404(CustomUser, id=user_id)
        except Http404:
            return Response("Invalid user please check the user id again.", status=status.HTTP_404_NOT_FOUND)
        serializer = UserSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, user_id):
        try:
            user = get_object_or_404(CustomUser, id=user_id)
        except Http404:
            return Response("Invalid user please check the user id again.", status=status.HTTP_404_NOT_FOUND)
        user.delete()
        return Response(
            {"message": "User deleted successfully"}, 
            status=status.HTTP_204_NO_CONTENT
        )


class AdminOrderListView(APIView):
    permission_classes = [IsAuthenticated, IsStaff]

    def get(self, request):
        orders = Order.objects.all().order_by('-created_at')

        status_filter = request.query_params.get('status')
        user_id = request.query_params.get('user_id')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        
        if status_filter:
            orders = orders.filter(status=status_filter.upper())
        if user_id:
            orders = orders.filter(user_id=user_id)
        if date_from:
            orders = orders.filter(created_at__date__gte=date_from)
        if date_to:
            orders = orders.filter(created_at__date__lte=date_to)
        
        paginator = MenuInfiniteScrollPagination()
        queryset = paginator.paginate_queryset(orders, request)
        serializer = OrderSerializer(queryset, many=True)
        return paginator.get_paginated_response(serializer.data)


class AdminOrderDetailView(APIView):
    permission_classes = [IsAuthenticated, IsStaff]

    def get(self, request, order_id):
        try:
            order = get_object_or_404(Order, id=order_id)
        except Http404:
            return Response(f"Corresponding order with id {order_id} not found.", status=status.HTTP_404_NOT_FOUND)
        serializer = OrderSerializer(order)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, order_id):
        try:
            order = get_object_or_404(Order, id=order_id)
        except Http404:
            return Response(f"Corresponding order with id {order_id} not found.", status=status.HTTP_404_NOT_FOUND)
        serializer = OrderSerializer(order, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, order_id):
        try:
            order = get_object_or_404(Order, id=order_id)
        except Http404:
            return Response(f"Corresponding order with id {order_id} not found.", status=status.HTTP_404_NOT_FOUND)
        
        if order.status not in ['CANCELLED', 'DELIVERED']:
            return Response(
                {"error": "Can only delete cancelled or delivered orders"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        order.delete()
        return Response(
            {"message": "Order deleted successfully"}, 
            status=status.HTTP_204_NO_CONTENT
        )


class AdminSubscriptionManagementView(APIView):
    permission_classes = [IsAuthenticated, IsStaff]

    def get(self, request):
        subscriptions = Subscription.objects.all()
        serializer = SubscriptionSerializer(subscriptions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = SubscriptionSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AdminSubscriptionDetailView(APIView):
    permission_classes = [IsAuthenticated, IsStaff]

    def get(self, request, sid):
        try:
            subscription = get_object_or_404(Subscription, sid=sid)
        except Http404:
            return Response("Subscription detail not foun.", status=status.HTTP_404_NOT_FOUND)
        serializer = SubscriptionSerializer(subscription)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, sid):
        try:
            subscription = get_object_or_404(Subscription, sid=sid)
        except Http404:
            return Response("Subscription details not found.", status=status.HTTP_404_NOT_FOUND)
        serializer = SubscriptionSerializer(subscription, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, sid):
        try:
            subscription = get_object_or_404(Subscription, sid=sid)
        except Http404:
            return Response("Subscriptiond detail not found.", status=status.HTTP_404_NOT_FOUND)
        
        active_users = UserSubscription.objects.filter(plan=subscription, is_active=True).count()
        if active_users > 0:
            return Response(
                {"error": f"Cannot delete subscription. {active_users} active users are using it."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        subscription.delete()
        return Response(
            {"message": "Subscription deleted successfully"}, 
            status=status.HTTP_204_NO_CONTENT
        )


class AdminUserSubscriptionListView(APIView):
    permission_classes = [IsAuthenticated, IsStaff]

    def get(self, request):
        subscriptions = UserSubscription.objects.all().order_by('-created_at')
        is_active = request.query_params.get('is_active')
        plan_type = request.query_params.get('plan_type')
        
        if is_active is not None:
            subscriptions = subscriptions.filter(is_active=is_active.lower() == 'true')
        if plan_type:
            subscriptions = subscriptions.filter(plan__subscription=plan_type.upper())
        
        paginator = MenuInfiniteScrollPagination()
        queryset = paginator.paginate_queryset(subscriptions, request)
        serializer = UserSubscriptionSerializer(queryset, many=True)
        return paginator.get_paginated_response(serializer.data)


class AdminUserSubscriptionDetailView(APIView):
    permission_classes = [IsAuthenticated, IsStaff]

    def get(self, request, sub_id):
        try:
            subscription = get_object_or_404(UserSubscription, sub_id=sub_id)
        except Http404:
            return Response("User Subscription not found.", status=status.HTTP_404_NOT_FOUND)
        serializer = UserSubscriptionSerializer(subscription)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, sub_id):
        try:
            subscription = get_object_or_404(UserSubscription, sub_id=sub_id)
        except Http404:
            return Response("User Subscription not found.", status=status.HTTP_404_NOT_FOUND)
        serializer = UserSubscriptionSerializer(subscription, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, sub_id):
        subscription = get_object_or_404(UserSubscription, sub_id=sub_id)
        subscription.is_active = False
        subscription.save()
        
        user = subscription.user
        user.status = False
        user.save()
        
        return Response(
            {"message": "User subscription cancelled successfully"}, 
            status=status.HTTP_200_OK
        )


class AdminMealAvailabilityView(APIView):
    permission_classes = [IsAuthenticated, IsStaff]

    def patch(self, request, meal_id):
        try:
            meal = get_object_or_404(Meals, meal_id=meal_id)
        except Http404:
            return Response("Meal object not found.", status=status.HTTP_404_NOT_FOUND)
        
        is_available = request.data.get('is_available')
        if is_available is None:
            return Response(
                {"error": "is_available field is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        if hasattr(meal, 'is_available'):
            meal.is_available = is_available
            meal.save()
            serializer = MealSerializer(meal)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response(
                {"error": "is_available field not found in Meals model. Please add it."}, 
                status=status.HTTP_400_BAD_REQUEST
            )


class AdminCustomMealListView(APIView):
    permission_classes = [IsAuthenticated, IsStaff]

    def get(self, request):
        custom_meals = CustomMeal.objects.all().order_by('-created_at')
        user_id = request.query_params.get('user_id')
        category = request.query_params.get('category')
        is_active = request.query_params.get('is_active')
        
        if user_id:
            custom_meals = custom_meals.filter(user_id=user_id)
        if category:
            custom_meals = custom_meals.filter(category=category)
        if is_active is not None:
            custom_meals = custom_meals.filter(is_active=is_active.lower() == 'true')
        
        paginator = MenuInfiniteScrollPagination()
        queryset = paginator.paginate_queryset(custom_meals, request)
        serializer = CustomMealSerializer(queryset, many=True)
        return paginator.get_paginated_response(serializer.data)


class AdminCustomMealDetailView(APIView):
    permission_classes = [IsAuthenticated, IsStaff]

    def get(self, request, combo_id):
        try:
            custom_meal = get_object_or_404(CustomMeal, combo_id=combo_id)
        except Http404:
            return Response("Custom meal not found with this id.", status=status.HTTP_404_NOT_FOUND)
        serializer = CustomMealSerializer(custom_meal)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, combo_id):
        try:
            custom_meal = get_object_or_404(CustomMeal, combo_id=combo_id)
        except Http404:
            return Response("Custom meal not found with this id.", status=status.HTTP_404_NOT_FOUND)
        custom_meal.delete()
        return Response(
            {"message": "Custom meal deleted successfully"}, 
            status=status.HTTP_204_NO_CONTENT
        )


class AdminStatisticsView(APIView):
    permission_classes = [IsAuthenticated, IsStaff]

    def get(self, request):
        
        total_users = CustomUser.objects.count()
        active_users = CustomUser.objects.filter(is_active=True).count()
        subscribed_users = CustomUser.objects.filter(status=True).count()

        total_orders = Order.objects.count()
        pending_orders = Order.objects.filter(status='PENDING').count()
        processing_orders = Order.objects.filter(status='PROCESSING').count()
        delivering_orders = Order.objects.filter(status='DELIVERING').count()
        delivered_orders = Order.objects.filter(status='DELIVERED').count()
        cancelled_orders = Order.objects.filter(status='CANCELLED').count()

        total_revenue = Order.objects.filter(
            status__in=['DELIVERED']
        ).aggregate(total=Sum('total_price'))['total'] or 0
        total_meals = Meals.objects.count()
        veg_meals = Meals.objects.filter(type='VEG').count()
        non_veg_meals = Meals.objects.filter(type='NON-VEG').count()
        total_custom_meals = CustomMeal.objects.count()
        active_custom_meals = CustomMeal.objects.filter(is_active=True).count()
        active_subscriptions = UserSubscription.objects.filter(is_active=True).count()
        expired_subscriptions = UserSubscription.objects.filter(is_active=False).count()
        
        statistics = {
            'users': {
                'total': total_users,
                'active': active_users,
                'subscribed': subscribed_users,
            },
            'orders': {
                'total': total_orders,
                'pending': pending_orders,
                'processing': processing_orders,
                'delivering': delivering_orders,
                'delivered': delivered_orders,
                'cancelled': cancelled_orders,
            },
            'revenue': {
                'total': str(total_revenue),
            },
            'meals': {
                'total': total_meals,
                'veg': veg_meals,
                'non_veg': non_veg_meals,
            },
            'custom_meals': {
                'total': total_custom_meals,
                'active': active_custom_meals,
            },
            'subscriptions': {
                'active': active_subscriptions,
                'expired': expired_subscriptions,
            }
        }
        
        return Response(statistics, status=status.HTTP_200_OK)