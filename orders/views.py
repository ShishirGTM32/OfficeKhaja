from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import transaction
from django.http import Http404
from datetime import timedelta
from decimal import Decimal
from khaja.models import Meals, CustomMeal
from users.models import UserSubscription, CustomUser
from .pagination import MenuInfiniteScrollPagination
from users.views import check_subscription
from orders.models import Order, Cart, CartItem, OrderItem, ComboOrderItem
from .permissions import IsStaff, IsSubscribedUser
from .serializers import (
    OrderSerializer, CartItemSerializer, CartItemDetialSerializer
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
            try:
                custom_meal = CustomMeal.objects.get(
                    combo_id=custom_meal_id, 
                    user=request.user,
                    is_active=True
                )
                
                if custom_meal.delivery_date < timezone.localdate():
                    return Response({
                        "error": "Delivery time cannot be in past. Please change the delivery time of the custom meal you created."
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                existing_item = CartItem.objects.filter(
                    cart=cart,
                    custom_meal_id=custom_meal_id,
                ).first()

                if existing_item:
                    return Response({
                        "error": "Custom meal already in cart. Number of servings is already specified."
                    }, status=status.HTTP_400_BAD_REQUEST)
                
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
                meal = Meals.objects.get(meal_id=meal_id, is_available=True)
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
                    "error": "Meal not found or not available"
                }, status=status.HTTP_404_NOT_FOUND)
            
    def delete(self, request):
        pk = request.data.get('pk')
        if pk:
            try:
                cart_item = get_object_or_404(CartItem, pk=pk, cart__user=request.user)
            except Http404:
                return Response({"error": "Cart item not found"}, status=status.HTTP_404_NOT_FOUND)
            cart_item.delete()
            return Response(
                status=status.HTTP_204_NO_CONTENT
            )
        else:
            try:
                cart = get_object_or_404(Cart, user=request.user)
            except Http404:
                return Response({"error": "Cart not found"}, status=status.HTTP_404_NOT_FOUND)
            cart.clear()
            return Response(
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
            return Response({"error": "Cart item not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = CartItemDetialSerializer(cart_item)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, pk):
        try:
            cart_item = self.get_object(pk, request.user)
        except Http404:
            return Response(status=status.HTTP_404_NOT_FOUND)
        cart_item.delete()
        return Response(
            status=status.HTTP_204_NO_CONTENT
        )


class CartItemUpdateView(APIView):
    permission_classes = [IsSubscribedUser]

    def patch(self, request, pk):
        try:
            cart_item = get_object_or_404(CartItem, pk=pk, cart__user=request.user)
        except Http404:
            return Response({"error": "Cart item not found"}, status=status.HTTP_404_NOT_FOUND)
        
        action = request.data.get('action')
        quantity = request.data.get('quantity')
        
        if action == 'increase':
            cart_item.quantity += 1
        elif action == 'decrease':
            if cart_item.quantity > 1:
                cart_item.quantity -= 1
            else:
                return Response(
                    {"error": "Quantity cannot be less than 1. Use delete to remove item."},
                    status=status.HTTP_400_BAD_REQUEST
                )
        elif quantity is not None:
            quantity = int(quantity)
            if quantity < 1:
                return Response(
                    {"error": "Quantity must be at least 1"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            cart_item.quantity = quantity
        else:
            return Response(
                {"error": "Provide either 'action' (increase/decrease) or 'quantity'"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        cart_item.save()
        serializer = CartItemSerializer(cart_item)
        return Response(serializer.data, status=status.HTTP_200_OK)


class OrderPreviewView(APIView):
    permission_classes = [IsSubscribedUser]

    def get(self, request):
        user = request.user
        cart = Cart.objects.filter(user=user).first()
        cart_item_ids = request.data.get("cart_item_id")
        if not cart or not cart.cart_items.exists():
            preview = {
                "subtotal": 0,
                "tax": 0,
                "delivery_charge": 0,
                "total": 0,
                "items_count": 0,
                "has_custom_meals": False,
                "has_regular_meals": False,
                "delivery_address": {
                    "default": request.user.street_address,
                },
                "payment_method": {
                    "method": user.payment_method if user.payment_method else None,
                    "note": "Using your default payment method"
                }
            }
        
            return Response(preview, status=status.HTTP_200_OK)

        cart_items = cart.cart_items.all()
        if cart_item_ids:
            cart_items = cart_items.filter(id__in=cart_item_ids)
        has_custom_meals = cart_items.filter(custom_meal__isnull=False).exists()
        has_regular_meals = cart_items.filter(meals__isnull=False).exists()
        
        custom_meal_addresses = []
        if has_custom_meals:
            custom_meal_addresses = list(
                cart_items.filter(custom_meal__isnull=False)
                .values_list('custom_meal__delivery_address', flat=True)
                .distinct()
            )
        
        default_address = str(user.street_address) if user.street_address else 'None'
        
        subtotal = sum(item.get_total_price() for item in cart_items)
        tax = subtotal * Decimal(0.13)
        delivery_charge = Decimal(50.00) if cart_items.exists() else Decimal(0)
        total = subtotal + tax + delivery_charge
        items_count = cart_items.count()

        preview = {
            "subtotal": float(subtotal),
            "tax": float(tax),
            "delivery_charge": float(delivery_charge),
            "total": float(total),
            "items_count": items_count,
            "has_custom_meals": has_custom_meals,
            "has_regular_meals": has_regular_meals,
            "delivery_address": {
                "default": default_address,
                "editable": has_regular_meals and not has_custom_meals,
                "custom_meal_addresses": custom_meal_addresses if has_custom_meals else [],
                "note": "Custom meals will be delivered to their pre-set addresses" if has_custom_meals else None
            },
            "payment_method": {
                "method": user.payment_method if user.payment_method else None,
                "note": "Using your default payment method"
            }
        }

        return Response(preview, status=status.HTTP_200_OK)


class OrderListView(APIView):
    def get_permissions(self):
        if self.request.method in ['GET']:
            permission_classes = [IsSubscribedUser]
        else:
            permission_classes = [IsStaff]
        return [permission() for permission in permission_classes]

    def get(self, request):
        status_filter = request.query_params.get('status', None)
        orders = Order.objects.filter(user=request.user)
        
        if status_filter:
            orders = orders.filter(status=status_filter.upper())
        serializer = OrderSerializer(orders, many=True)
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
            return Response({"error": "Order not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = OrderSerializer(order)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def patch(self, request, pk):
        data = request.data
        try:
            order = get_object_or_404(Order, pk=pk, user=request.user)
        except Http404:
            return Response({"error": "Order not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = OrderSerializer(order, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)


class OrderCancelView(APIView):
    permission_classes = [IsAuthenticated, IsSubscribedUser]

    def post(self, request, pk):
        try:
            order = get_object_or_404(Order, pk=pk, user=request.user)
        except Http404:
            return Response({"error": "Order not found"}, status=status.HTTP_404_NOT_FOUND)

        if order.status not in ['PENDING']:
            return Response(
                {"error": f"Cannot cancel order with status: {order.status}. Only pending orders can be cancelled."},
                status=status.HTTP_400_BAD_REQUEST
            )
        order.status = 'CANCELLED'
        order.save()

        serializer = OrderSerializer(order)
        return Response({
            "success": True,
            "message": "Order cancelled successfully",
            "order": serializer.data
        }, status=status.HTTP_200_OK)


class OrderCreateView(APIView):
    permission_classes = [IsSubscribedUser]

    def post(self, request):
        user = get_object_or_404(CustomUser, pk=request.user.id)
        
        if check_subscription(request.user):
            return Response(
                {"error": "Subscription not renewed. Please renew to place orders."},
                status=status.HTTP_403_FORBIDDEN
            )

        cart = Cart.objects.filter(user=request.user).first()
        if not cart or not cart.cart_items.exists():
            return Response(
                {"error": "Your cart is empty"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        cart_item_ids = request.data.get('cart_id')

        cart_items = cart.cart_items.all()
        if cart_item_ids:
            cart_items = cart_items.filter(id__in=cart_item_ids)
        has_custom_meals = cart_items.filter(custom_meal__isnull=False).exists()
        has_regular_meals = cart_items.filter(meals__isnull=False).exists()
        
        delivery_address_for_regular = request.data.get('delivery_address')
        if has_regular_meals and not delivery_address_for_regular:
            delivery_address_for_regular = str(user.street_address) if user.street_address else ''
            if not delivery_address_for_regular:
                return Response(
                    {"error": "Delivery address is required for regular meals"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        if not user.payment_method:
            return Response(
                {"error": "Please set a default payment method in your profile"},
                status=status.HTTP_400_BAD_REQUEST
            )

        for cart_item in cart_items:
            if cart_item.custom_meal:
                if cart_item.custom_meal.delivery_date < timezone.localdate():
                    return Response({
                        "error": f"Custom meal '{cart_item.custom_meal.meal_category.category}' has delivery time in the past. Please update it before ordering."
                    }, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            if has_custom_meals and has_regular_meals:
                order = Order.objects.create(
                    user=user,
                    delivery_address="Multiple addresses (see items)",
                    payment_method=user.payment_method,
                )
            elif has_custom_meals:
                first_custom = cart_items.filter(custom_meal__isnull=False).first()
                order = Order.objects.create(
                    user=user,
                    delivery_address=first_custom.custom_meal.delivery_address,
                    payment_method=user.payment_method,
                )
            else:
                order = Order.objects.create(
                    user=user,
                    delivery_address=delivery_address_for_regular,
                    payment_method=user.payment_method,
                )

            for cart_item in cart_items:
                if cart_item.custom_meal:
                    custom_meal = cart_item.custom_meal
                    subscription = UserSubscription.objects.filter(user=request.user).first()
                    
                    if not subscription:
                        raise Exception("No active subscription found")
                    
                    price_snapshot = custom_meal.get_total_price()
                    delivery_from = custom_meal.delivery_date
                    delivery_to = delivery_from + timedelta(days=subscription.plan.duration_days - 1)
                    delivery_time_slot = custom_meal.delivery_time_slot
                    ComboOrderItem.objects.create(
                        order=order,
                        combo=custom_meal,
                        delivery_from_date=delivery_from,
                        delivery_to_date=delivery_to,
                        delivery_time_slot = delivery_time_slot,
                        quantity=cart_item.quantity,
                        preferences=custom_meal.preferences,
                        price_snapshot=price_snapshot,
                    )

                elif cart_item.meals:
                    meal = cart_item.meals
                    OrderItem.objects.create(
                        order=order,
                        meals=meal,
                        meal_type=meal.type.type_name,
                        meal_category=meal.meal_category.category,
                        quantity=cart_item.quantity
                    )

            order.calculate_pricing()
            if not cart_item_ids:
                cart.clear()
            else:
                cart.cart_items.filter(id__in=cart_item_ids).delete()


            order_serializer = OrderSerializer(order, context={'request': request})
            return Response({
                "success": True,
                "message": "Order placed successfully",
                "order": order_serializer.data
            }, status=status.HTTP_201_CREATED)


class OrderReorderToCartView(APIView):
    permission_classes = [IsSubscribedUser]

    def post(self, request, pk):
        original_order = get_object_or_404(Order, pk=pk, user=request.user)
        if original_order.status not in ["DELIVERED", "CANCELLED"]:
            return Response(
                {"error": f"Cannot reorder order with status {original_order.status}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        cart, _ = Cart.objects.get_or_create(user=request.user)
        added_items = []

        for item in original_order.order_items.all():
            existing_item = CartItem.objects.filter(cart=cart, meals=item.meals).first()
            if existing_item:
                existing_item.quantity += item.quantity
                existing_item.save()
            else:
                CartItem.objects.create(
                    cart=cart,
                    meals=item.meals,
                    quantity=item.quantity
                )
            added_items.append({
                "type": "meal",
                "meal_id": item.meals.id,
                "name": item.meals.name,
                "quantity": item.quantity
            })

        for combo_item in original_order.combo_items.all():
            combo = combo_item.combo
            existing_item = CartItem.objects.filter(cart=cart, custom_meal=combo).first()
            if existing_item:
                existing_item.quantity += combo_item.quantity
                existing_item.save()
            else:
                CartItem.objects.create(
                    cart=cart,
                    custom_meal=combo,
                    quantity=combo_item.quantity
                )
            added_items.append({
                "type": "combo",
                "combo_id": str(combo.combo_id),
                "quantity": combo_item.quantity
            })

        return Response({
            "success": True,
            "message": "Items added to cart from previous order",
            "added_items": added_items
        }, status=status.HTTP_200_OK)


class OrderStatusChoicesView(APIView):
    permission_classes = [IsStaff]

    def get(self, request):
        return Response({
            "order_statuses": [
                {"value": "CANCELLED", "label": "Cancelled"},
                {"value": "PENDING", "label": "Pending"},
                {"value": "PROCESSING", "label": "Processing"},
                {"value": "DELIVERING", "label": "Delivering"},
                {"value": "DELIVERED", "label": "Delivered"}
            ]
        }, status=status.HTTP_200_OK)