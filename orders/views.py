from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone
from khaja.models import Meals, CustomMeal, Combo
from users.models import UserSubscription, CustomUser
from django.db import transaction
from datetime import  timedelta
from django.http import Http404
from .permissions import IsStaff, IsSubscribedUser
from khaja.pagination import MenuInfiniteScrollPagination
from users.views import check_subscription
from orders.models import Order, Cart, CartItem, OrderItem, ComboOrderItem
from .serializers import (
    OrderSerializer, CartItemSerializer, OrderCreateSerializer
)

class CartListView(APIView):
    def get_permissions(self):
        if self.request.method in ['GET', 'POST', 'DELETE']:
            permission_classes = [IsSubscribedUser]
        else:
            permission_classes = [IsStaff]
        return [permission() for permission in permission_classes]

    def get(self, request):
        cart, created = Cart.objects.get_or_create(user=request.user)
        cart_items = cart.cart_items.all()
        paginator = MenuInfiniteScrollPagination()
        queryset = paginator.paginate_queryset(cart_items, request)
        serializer = CartItemSerializer(queryset, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):

        cart, created = Cart.objects.get_or_create(user=request.user)

        custom_meal_id = request.data.get('custom_meal_id')
        meal_id = request.data.get('meal_id')
        quantity = int(request.data.get('quantity', 1))

        if not custom_meal_id and not meal_id:
            return Response({
                "error": "Either meal_id or custom_meal_id is required"
            }, status=status.HTTP_400_BAD_REQUEST)

        if quantity <= 0:
            return Response({
                "error": "Quantity must be greater than 0"
            }, status=status.HTTP_400_BAD_REQUEST)

        if custom_meal_id:
            custom_meal = CustomMeal.objects.get(combo_id=custom_meal_id)
            if custom_meal.delivery_time < timezone.now():
                return Response("delivery time cannot be in past. Please change the delivery time of the custom meal you created.", status=status.HTTP_400_BAD_REQUEST)
            try:
                custom_meal = CustomMeal.objects.get(
                    combo_id=custom_meal_id, 
                    user=request.user,
                    is_active=True
                )
                existing_item = CartItem.objects.filter(
                    cart=cart,
                    custom_meal_id=custom_meal_id,
                ).first()

                if existing_item:
                    return Response("No of servings already specified so quantity only 1 for combo items if placed.")
                cart_item = CartItem.objects.create(
                    cart=cart,
                    custom_meal_id=custom_meal_id,
                    quantity=quantity,
                )
                serializer = CartItemSerializer(cart_item)
                return Response(serializer.data, status=status.HTTP_201_CREATED)

            except CustomMeal.DoesNotExist:
                return Response({
                    "error": "Custom meal not found or doesn't belong to you"
                }, status=status.HTTP_404_NOT_FOUND)

        elif meal_id:
            try:
                meal = Meals.objects.get(meal_id=meal_id)
                existing_item = CartItem.objects.filter(
                    cart=cart,
                    meals=meal,
                ).first()

                if existing_item:
                    existing_item.quantity += quantity
                    existing_item.save()
                    serializer = CartItemSerializer(existing_item)
                    return Response(serializer.data, status=status.HTTP_200_OK)

                cart_item = CartItem.objects.create(
                    cart=cart,
                    meals=meal,
                    quantity=quantity,
                )

                serializer = CartItemSerializer(cart_item)
                return Response(serializer.data, status=status.HTTP_201_CREATED)

            except Meals.DoesNotExist:
                return Response({
                    "error": "Meal not found"
                }, status=status.HTTP_404_NOT_FOUND)
            
    def delete(self, request):
        pk = request.data.get('pk')
        if pk:
            try:
                cart_item = get_object_or_404(CartItem, pk=pk, cart__user=request.user)
            except Http404:
                return Response("Cart Item not found", status=status.HTTP_404_NOT_FOUND)
            cart_item.delete()
            return Response(
                {"message": "Item removed from cart"}, 
                status=status.HTTP_204_NO_CONTENT
            )
        else:
            try:
                cart = get_object_or_404(Cart, cart__user=request.user)
            except Http404:
                return Response("Cart not found", status=status.HTTP_404_NOT_FOUND)
            cart.clear()
            return Response(
                {"message": "Cart cleared successfully"}, 
                status=status.HTTP_204_NO_CONTENT
            )


class CartItemDetailView(APIView):
    def get_permissions(self):
        if self.request.method in ['GET', 'DELETE']:
            permission_classes = [IsSubscribedUser]
        else:
            permission_classes = [IsStaff]
        return [permission() for permission in permission_classes]

    def get_object(self, pk, user):
        return get_object_or_404(CartItem, pk=pk, cart__user=user)

    def get(self, request, pk):
        try:
            cart_item = self.get_object(pk, request.user)
        except Http404:
            return Response("Cart item not found", status= status.HTTP_404_NOT_FOUND)
        serializer = CartItemSerializer(cart_item)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, pk):
        try:
            cart_item = self.get_object(pk, request.user)
        except Http404:
            return Response("Cart item not found", status= status.HTTP_404_NOT_FOUND)
        cart_item.delete()
        return Response(
            {"message": "Item removed from cart"}, 
            status=status.HTTP_204_NO_CONTENT
        )


class OrderListView(APIView):
    def get_permissions(self):
        if self.request.method in ['GET', 'POST']:
            permission_classes = [IsSubscribedUser]
        else:
            permission_classes = [IsStaff]
        return [permission() for permission in permission_classes]

    def get(self, request):
        status_filter = request.query_params.get('status', None)
        orders = Order.objects.filter(user=request.user)
        
        if status_filter:
            orders = orders.filter(status=status_filter.upper())
        paginator = MenuInfiniteScrollPagination()
        queryset = paginator.paginate_queryset(orders, request)
        serializer = OrderSerializer(queryset, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = OrderCreateSerializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        validated_data = serializer.validated_data
        user = get_object_or_404(CustomUser, pk=request.user.id)

        cart = Cart.objects.filter(user=request.user).first()
        if not cart:
            return Response({"error": "No cart found"}, status=status.HTTP_400_BAD_REQUEST)

        cart_item_ids = validated_data.get('cart_item_ids', [])
        if cart_item_ids:
            cart_items = cart.cart_items.filter(id__in=cart_item_ids)
        else:
            cart_items = cart.cart_items.all()

        if not cart_items.exists():
            return Response(
                {"error": "No items in cart to order"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            order = Order.objects.create(
                user=user,
                delivery_address=validated_data.get('delivery_address', user.street_address),
                payment_method=user.payment_method, 
            )

            for cart_item in cart_items:
                if cart_item.custom_meal:
                    custom_meal = cart_item.custom_meal
                    subscription = UserSubscription.objects.get(user=request.user)
                    if check_subscription(request.user):
                        return Response("Subscription not renewed", status=status.HTTP_403_FORBIDDEN)
                    price_snapshot = custom_meal.get_total_price()
                    if custom_meal.delivery_time < timezone.now():
                        return Response("Delivery date is not present time, is in past. Re-Change the date and proceed to order.", status=status.HTTP_403_FORBIDDEN) 
                    delivery_from = custom_meal.delivery_time.date()
                    delivery_to = delivery_from + timedelta(days=subscription.plan.duration_days - 1)

                    ComboOrderItem.objects.create(
                        order=order,
                        combo=custom_meal,
                        subscription_plan=subscription.plan.subscription,
                        delivery_from_date=delivery_from,
                        delivery_to_date=delivery_to,
                        delivery_time=custom_meal.delivery_time.time(),
                        quantity=cart_item.quantity,
                        preferences=custom_meal.preferences,
                        price_snapshot=price_snapshot,
                    )

                elif cart_item.meals:
                    meal = cart_item.meals


                    OrderItem.objects.create(
                        order=order,
                        meals=meal,
                        meal_type=meal.type,
                        meal_category=meal.meal_category,
                        quantity=cart_item.quantity
                    )

            order.calculate_pricing()

            cart_items.delete()

            order_serializer = OrderSerializer(order, context={'request': request})
            return Response(order_serializer.data, status=status.HTTP_201_CREATED)
        
    def patch(self, request):
        pk = request.data.get("order_id")
        data = request.data
        try:
            order = get_object_or_404(Order, pk=pk)
        except Http404:
            return Response("Order not found please enter valid order id.", status=status.HTTP_404_NOT_FOUND)
        serializer = OrderSerializer(order, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)


class OrderDetailView(APIView):
    def get_permissions(self):
        if self.request.method in ['GET']:
            permission_classes = [IsAuthenticated, IsSubscribedUser]
        else:
            permission_classes = [IsStaff]
        return [permission() for permission in permission_classes]
    

    def get_object(self, pk, user):
        return get_object_or_404(Order, pk=pk, user=user)

    def get(self, request, pk):
        try:
            order = self.get_object(pk, request.user)
        except Http404:
            return Response("Order not found please enter valid order id.", status=status.HTTP_404_NOT_FOUND)
        serializer = OrderSerializer(order)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def patch(self, request, pk):
        data = request.data
        try:
            order = get_object_or_404(Order, pk=pk)
        except Http404:
            return Response("Order not found please enter valid order id.", status=status.HTTP_404_NOT_FOUND)
        serializer = OrderSerializer(order, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

class OrderCancelView(APIView):
    def get_permissions(self):
        if self.request.method in ['POST']:
            permission_classes = [IsAuthenticated, IsSubscribedUser]
        else:
            permission_classes = [IsStaff]
        return [permission() for permission in permission_classes]

    def post(self, request, pk):
        try:
            order = get_object_or_404(Order, pk=pk, user=request.user)
        except Http404:
            return Response("Order not found please enter valid order id.", status=status.HTTP_404_NOT_FOUND)

        if order.status not in ['PENDING']:
            return Response(
                {"error": f"Cannot cancel order with status: {order.status}"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        order.status = 'CANCELLED'
        order.save()

        serializer = OrderSerializer(order)
        return Response(
            {"message": "Order cancelled successfully", "order": serializer.data}, 
            status=status.HTTP_200_OK
        )