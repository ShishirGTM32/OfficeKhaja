from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404
from khaja.models import Meals, CustomMeal
from decimal import Decimal
from orders.models import Order, Cart, CartItem, OrderItem
from .serializers import (
    OrderSerializer, OrderCreateSerializer, CartSerializer, CartItemSerializer
)


class CartView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        cart, created = Cart.objects.get_or_create()
        serializer = CartSerializer(cart)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request):
        cart = get_object_or_404(Cart, user=request.user)
        cart.clear()
        return Response(
            {"message": "Cart cleared successfully"}, 
            status=status.HTTP_204_NO_CONTENT
        )


class CartItemListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        cart, created = Cart.objects.get_or_create()
        cart_items = cart.cart_items.all()
        serializer = CartItemSerializer(cart_items, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        cart, created = Cart.objects.get_or_create()
        custom_meal_id = request.data.get('custom_meal_id')
        meal_id = request.data.get("meal_id")
        if custom_meal_id or meal_id:
            if custom_meal_id:
                try:
                    custom_meal = CustomMeal.objects.get(combo_id=custom_meal_id)
                    existing_item = CartItem.objects.filter(cart=cart, custom_meal=custom_meal.combo_id).first()

                    if existing_item:
                        existing_item.quantity += int(request.data.get('quantity', 1))
                        existing_item.save()
                        serializer = CartItemSerializer(existing_item)
                        return Response(serializer.data, status=status.HTTP_200_OK)
        
                except CustomMeal.DoesNotExist:
                    return Response({"error": "Custom meal not found or doesn't belong to you"}, status=status.HTTP_404_NOT_FOUND)        
            elif meal_id:
                try:
                    meal = Meals.objects.get(meal_id=meal_id)
                    existing_item = CartItem.objects.filter(cart=cart, meals_id = meal.meal_id).first()

                    if existing_item:
                        existing_item.quantity += int(request.data.get('quantity', 1))
                        existing_item.save()
                        serializer = CartItemSerializer(existing_item)
                        return Response(serializer.data, status=status.HTTP_200_OK)

                except Meals.DoesNotExist:
                    return Response({"error": "Meal id not found."}, status=status.HTTP_404_NOT_FOUND)
            
            else:
                return Response({"error":"Meal id or custom meal id is required"}, status=status.HTTP_404_NOT_FOUND)
            
        serializer = CartItemSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            if custom_meal_id:
                serializer.save(cart=cart, custom_meal=custom_meal)
            elif meal_id:
                serializer.save(cart=cart, meals_id = meal.meal_id)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CartItemDetailView(APIView):
    permission_classes = [AllowAny]

    def get_object(self, pk, user):
        return get_object_or_404(CartItem, pk=pk, cart__user=user)

    def get(self, request, pk):
        cart_item = self.get_object(pk, request.user)
        serializer = CartItemSerializer(cart_item)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, pk):
        cart_item = self.get_object(pk, request.user)
        quantity = request.data.get('quantity')

        if quantity:
            if int(quantity) <= 0:
                return Response({"error": "Quantity must be greater than 0"}, status=status.HTTP_400_BAD_REQUEST)
            cart_item.quantity = quantity
            cart_item.save()

        serializer = CartItemSerializer(cart_item)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, pk):
        cart_item = self.get_object(pk, request.user)
        cart_item.delete()
        return Response({"message": "Item removed from cart"}, status=status.HTTP_204_NO_CONTENT)


class OrderListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        status_filter = request.query_params.get('status', None)
        orders = Order.objects.filter()

        if status_filter:
            orders = orders.filter(status=status_filter.upper())

        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = OrderCreateSerializer(data=request.data, context={'request': request})

        if serializer.is_valid():
            cart = Cart.objects.filter().first()

            if not cart or not cart.cart_items.exists():
                return Response({"error": "Cart is empty"}, status=status.HTTP_400_BAD_REQUEST)

            order = Order.objects.create(
                delivery_address=serializer.validated_data['delivery_address'],
                delivery_time=serializer.validated_data['delivery_time'],
                payment_method=serializer.validated_data['payment_method'],
                notes=serializer.validated_data.get('notes', '')
            )

            for cart_item in cart.cart_items.all():
                meal_items_snapshot = []

                if cart_item.custom_meal:
                    custom_meal = cart_item.custom_meal
                    for meal in custom_meal.meals.meals.all():
                        meal_data = {
                            'meal_id': meal.meal_id,
                            'name': meal.name,
                            'type': meal.type,
                            'price': str(meal.price),
                            'weight': meal.weight
                        }
                        if hasattr(meal, 'meal_ingredients'):
                            ingredients = meal.meal_ingredients.get_ingredients()
                            meal_data['ingredients'] = [
                                {'id': ing.id, 'name': ing.name, 'category': ing.category}
                                for ing in ingredients
                            ]
                        if hasattr(meal, 'nutrition'):
                            meal_data['nutrition'] = {
                                'energy': str(meal.nutrition.energy),
                                'protein': str(meal.nutrition.protein),
                                'carbs': str(meal.nutrition.carbs),
                                'fats': str(meal.nutrition.fats),
                            }
                        meal_items_snapshot.append(meal_data)

                    OrderItem.objects.create(
                        order=order,
                        custom_meal=custom_meal,
                        meal_type=custom_meal.type,
                        meal_category=custom_meal.category,
                        no_of_servings=custom_meal.no_of_servings,
                        preferences=custom_meal.preferences,
                        subscription_plan=custom_meal.subscription_plan,
                        delivery_time=custom_meal.delivery_time,
                        price_per_serving=custom_meal.get_total_price() / custom_meal.no_of_servings if custom_meal.no_of_servings > 0 else Decimal('0.00'),
                        quantity=cart_item.quantity,
                        meal_items_snapshot=meal_items_snapshot
                    )

                elif cart_item.meals:
                    meal = cart_item.meals
                    meal_data = {
                        'meal_id': meal.meal_id,
                        'name': meal.name,
                        'type': meal.type,
                        'price': str(meal.price),
                        'weight': meal.weight
                    }
                    if hasattr(meal, 'meal_ingredients'):
                        ingredients = meal.meal_ingredients.get_ingredients()
                        meal_data['ingredients'] = [
                            {'id': ing.id, 'name': ing.name, 'category': ing.category}
                            for ing in ingredients
                        ]
                    if hasattr(meal, 'nutrition'):
                        meal_data['nutrition'] = {
                            'energy': str(meal.nutrition.energy),
                            'protein': str(meal.nutrition.protein),
                            'carbs': str(meal.nutrition.carbs),
                            'fats': str(meal.nutrition.fats),
                        }
                    meal_items_snapshot.append(meal_data)

                    OrderItem.objects.create(
                        order=order,
                        meals=meal,
                        meal_type=meal.type,
                        meal_category=meal.meal_category,
                        no_of_servings=1,
                        preferences='',
                        subscription_plan='ONE_TIME',
                        delivery_time=None,
                        price_per_serving=meal.price,
                        quantity=cart_item.quantity,
                        meal_items_snapshot=meal_items_snapshot
                    )

            order.calculate_pricing()
            cart.delete()
            order_serializer = OrderSerializer(order)
            return Response(order_serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class OrderDetailView(APIView):
    permission_classes = [AllowAny]

    def get_object(self, pk, user):
        return get_object_or_404(Order, pk=pk, user=user)

    def get(self, request, pk):
        order = self.get_object(pk, user=None)
        serializer = OrderSerializer(order)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, pk):
        order = self.get_object(pk)

        if 'status' in request.data:
            new_status = request.data['status']

            if new_status == 'CANCELLED':
                if order.status in ['PENDING', 'PROCESSING']:
                    order.status = 'CANCELLED'
                    order.save()
                else:
                    return Response({"error": "Cannot cancel order in current status"}, status=status.HTTP_400_BAD_REQUEST)
                order.status = new_status
                order.save()
            else:
                return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)

        if 'payment_status' in request.data and request.user.is_staff:
            order.payment_status = request.data['payment_status']
            order.save()

        serializer = OrderSerializer(order)
        return Response(serializer.data, status=status.HTTP_200_OK)


class OrderCancelView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk)

        if order.status not in ['PENDING', 'PROCESSING']:
            return Response({"error": f"Cannot cancel order with status: {order.status}"}, status=status.HTTP_400_BAD_REQUEST)

        order.status = 'CANCELLED'
        order.save()

        serializer = OrderSerializer(order)
        return Response({"message": "Order cancelled successfully", "order": serializer.data}, status=status.HTTP_200_OK)
