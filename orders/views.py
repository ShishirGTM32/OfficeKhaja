from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404
from django.utils import timezone
from khaja.models import Meals, CustomMeal, Combo
from decimal import Decimal
from datetime import datetime
from orders.models import Order, Cart, CartItem, ComboCartItem, OrderItem, ComboOrderItem
from .serializers import (
    OrderSerializer, CartSerializer, CartItemSerializer, ComboCartItemSerializer, OrderCreateSerializer )


class CartView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cart, created = Cart.objects.get_or_create(user_id=self.request.user.id)
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
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cart, created = Cart.objects.get_or_create(user=self.request.user.id)
        
        cart_items = cart.cart_items.all()
        combo_items = cart.combo_cart_items.all()
        
        cart_serializer = CartItemSerializer(cart_items, many=True)
        combo_serializer = ComboCartItemSerializer(combo_items, many=True)
        
        return Response({
            'cart_items': cart_serializer.data,
            'combo_items': combo_serializer.data
        }, status=status.HTTP_200_OK)

    def post(self, request):
        cart, created = Cart.objects.get_or_create(user_id=request.user.id)
        custom_meal_id = request.data.get('custom_meal_id')
        meal_id = request.data.get("meal_id")
        combo_id = request.data.get("combo_id")
        delivery_time_slot = request.data.get('delivery_time_slot')
        delivery_time = request.data.get('delivery_time')
        preferences = request.data.get('preferences', '')

        if combo_id:
            try:
                combo = Combo.objects.get(cid=combo_id)
                subscription_plan = request.data.get('subscription_plan')
                delivery_from_date = request.data.get('delivery_from_date')
                delivery_to_date = request.data.get('delivery_to_date')
                
                if not subscription_plan:
                    return Response({
                        "error": "Subscription plan is required for combo meals"
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                from_date = None
                to_date = None
                if delivery_from_date:
                    from_date = datetime.strptime(delivery_from_date, '%Y-%m-%d').date()
                if delivery_to_date:
                    to_date = datetime.strptime(delivery_to_date, '%Y-%m-%d').date()
                
                delivery_datetime = None
                if delivery_time:
                    delivery_datetime = datetime.fromisoformat(delivery_time.replace('Z', '+00:00'))
                
                existing_item = ComboCartItem.objects.filter(
                    cart=cart, 
                    combo=combo, 
                    subscription_plan=subscription_plan
                ).first()

                if existing_item:
                    existing_item.quantity += int(request.data.get('quantity', 1))
                    if delivery_time_slot:
                        existing_item.delivery_time_slot = delivery_time_slot
                    if delivery_datetime:
                        existing_item.delivery_time = delivery_datetime
                    existing_item.save()
                    serializer = ComboCartItemSerializer(existing_item)
                    return Response(serializer.data, status=status.HTTP_200_OK)
                
                combo_item = ComboCartItem.objects.create(
                    cart=cart,
                    combo=combo,
                    quantity=int(request.data.get('quantity', 1)),
                    subscription_plan=subscription_plan,
                    delivery_from_date=from_date,
                    delivery_to_date=to_date,
                    delivery_time_slot=delivery_time_slot,
                    delivery_time=delivery_datetime,
                    preferences=preferences
                )
                serializer = ComboCartItemSerializer(combo_item)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
                
            except Combo.DoesNotExist:
                return Response({"error": "Combo not found"}, status=status.HTTP_404_NOT_FOUND)
            
        if custom_meal_id:
            try:
                custom_meal = CustomMeal.objects.get(combo_id=custom_meal_id, user_id=request.user.id)
                
                delivery_datetime = None
                if delivery_time:
                    delivery_datetime = datetime.fromisoformat(delivery_time.replace('Z', '+00:00'))
                elif custom_meal.delivery_time:
                    delivery_datetime = custom_meal.delivery_time
                
                if not delivery_time_slot and custom_meal.delivery_time_slot:
                    delivery_time_slot = custom_meal.delivery_time_slot
                
                existing_item = CartItem.objects.filter(cart=cart, custom_meal=custom_meal).first()

                if existing_item:
                    existing_item.quantity += int(request.data.get('quantity', 1))
                    if delivery_time_slot:
                        existing_item.delivery_time_slot = delivery_time_slot
                    if delivery_datetime:
                        existing_item.delivery_time = delivery_datetime
                    if preferences:
                        existing_item.preferences = preferences
                    existing_item.save()
                    serializer = CartItemSerializer(existing_item)
                    return Response(serializer.data, status=status.HTTP_200_OK)
                
                cart_item = CartItem.objects.create(
                    cart=cart,
                    custom_meal=custom_meal,
                    quantity=int(request.data.get('quantity', 1)),
                    delivery_time_slot=delivery_time_slot,
                    delivery_time=delivery_datetime,
                    preferences=preferences
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

                delivery_datetime = None
                if delivery_time:
                    delivery_datetime = datetime.fromisoformat(delivery_time.replace('Z', '+00:00'))
                
                existing_item = CartItem.objects.filter(cart=cart, meals=meal).first()

                if existing_item:
                    existing_item.quantity += int(request.data.get('quantity', 1))
                    if delivery_time_slot:
                        existing_item.delivery_time_slot = delivery_time_slot
                    if delivery_datetime:
                        existing_item.delivery_time = delivery_datetime
                    if preferences:
                        existing_item.preferences = preferences
                    existing_item.save()
                    serializer = CartItemSerializer(existing_item)
                    return Response(serializer.data, status=status.HTTP_200_OK)
                
                cart_item = CartItem.objects.create(
                    cart=cart,
                    meals=meal,
                    quantity=int(request.data.get('quantity', 1)),
                    delivery_time_slot=delivery_time_slot,
                    delivery_time=delivery_datetime,
                    preferences=preferences
                )
                serializer = CartItemSerializer(cart_item)
                return Response(serializer.data, status=status.HTTP_201_CREATED)

            except Meals.DoesNotExist:
                return Response({"error": "Meal not found."}, status=status.HTTP_404_NOT_FOUND)
        else:
            return Response({
                "error": "Either meal_id, custom_meal_id, or combo_id is required"
            }, status=status.HTTP_400_BAD_REQUEST)


class CartItemDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk, user):
        item_type = self.request.query_params.get('type', 'meal')
        if item_type == 'combo':
            return get_object_or_404(ComboCartItem, pk=pk, cart__user=user)
        return get_object_or_404(CartItem, pk=pk, cart__user=user)

    def get(self, request, pk):
        cart_item = self.get_object(pk, request.user)
        item_type = request.query_params.get('type', 'meal')
        
        if item_type == 'combo':
            serializer = ComboCartItemSerializer(cart_item)
        else:
            serializer = CartItemSerializer(cart_item)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, pk):
        cart_item = self.get_object(pk, request.user)
        quantity = request.data.get('quantity')
        delivery_time_slot = request.data.get('delivery_time_slot')
        delivery_time = request.data.get('delivery_time')
        preferences = request.data.get('preferences')

        if quantity:
            if int(quantity) <= 0:
                return Response(
                    {"error": "Quantity must be greater than 0"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            cart_item.quantity = quantity
        
        if preferences is not None:
            cart_item.preferences = preferences
        
        if delivery_time_slot:
            valid_slots = [choice[0] for choice in CartItem.DELIVERY_TIME_SLOTS]
            if delivery_time_slot not in valid_slots:
                return Response(
                    {"error": f"Invalid delivery time slot. Choose from: {', '.join(valid_slots)}"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            cart_item.delivery_time_slot = delivery_time_slot
        if delivery_time:
            try:
                delivery_datetime = datetime.fromisoformat(delivery_time.replace('Z', '+00:00'))
                if delivery_datetime < timezone.now():
                    return Response(
                        {"error": "Delivery time must be in the future"}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
                cart_item.delivery_time = delivery_datetime
            except ValueError:
                return Response(
                    {"error": "Invalid datetime format. Use ISO format (YYYY-MM-DDTHH:MM:SS)"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        cart_item.save()

        item_type = request.query_params.get('type', 'meal')
        if item_type == 'combo':
            serializer = ComboCartItemSerializer(cart_item)
        else:
            serializer = CartItemSerializer(cart_item)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, pk):
        cart_item = self.get_object(pk, request.user)
        cart_item.delete()
        return Response(
            {"message": "Item removed from cart"}, 
            status=status.HTTP_204_NO_CONTENT
        )
    

class OrderListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        status_filter = request.query_params.get('status', None)
        orders = Order.objects.filter(user_id=self.request.user.id)

        if status_filter:
            orders = orders.filter(status=status_filter.upper())

        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = OrderCreateSerializer(data=request.data, context={'request': request})

        if serializer.is_valid():
            cart = Cart.objects.filter(user=request.user).first()
            cart_item_ids = serializer.validated_data.get('cart_item_ids', [])
            combo_item_ids = serializer.validated_data.get('combo_item_ids', [])
            
            # Get cart items
            if cart_item_ids:
                cart_items = cart.cart_items.filter(id__in=cart_item_ids)
            else:
                cart_items = cart.cart_items.all()
            
            # Get combo items
            if combo_item_ids:
                combo_items = cart.combo_cart_items.filter(id__in=combo_item_ids)
            else:
                combo_items = cart.combo_cart_items.all()

            if not cart or (not cart_items.exists() and not combo_items.exists()):
                return Response(
                    {"error": "No items in cart to order"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Create order
            order = Order.objects.create(
                user=request.user,
                notes=serializer.validated_data.get('notes', ''),
                delivery_address=serializer.validated_data.get(
                    'delivery_address', 
                    request.user.street_address
                ),
                payment_method=serializer.validated_data.get(
                    'payment_method', 
                    request.user.payment_method
                ),
            )

            # Process regular cart items
            for cart_item in cart_items:
                meal_items_snapshot = []

                if cart_item.custom_meal:
                    custom_meal = cart_item.custom_meal
                    for meal in custom_meal.meals.all():
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
                        meal_category=custom_meal.category,
                        no_of_servings=custom_meal.no_of_servings,
                        preferences=cart_item.preferences or custom_meal.preferences,
                        delivery_time_slot=cart_item.delivery_time_slot,
                        delivery_datetime=custom_meal.delivery_time,
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
                        meal_category=meal.meal_category if hasattr(meal, 'meal_category') else 'REGULAR',
                        no_of_servings=1,
                        preferences=cart_item.preferences,
                        delivery_time_slot=cart_item.delivery_time_slot,
                        price_per_serving=meal.price,
                        quantity=cart_item.quantity,
                        meal_items_snapshot=meal_items_snapshot
                    )

            # Process combo cart items
            for combo_item in combo_items:
                combo = combo_item.combo
                
                # Create snapshot of combo data
                combo_items_snapshot = {
                    'combo_id': combo.id,
                    'name': combo.name,
                    'description': combo.description if hasattr(combo, 'description') else '',
                    'price': str(combo.price)
                }
                
                ComboOrderItem.objects.create(
                    order=order,
                    combo=combo,
                    subscription_plan=combo_item.subscription_plan,
                    delivery_from_date=combo_item.delivery_from_date,
                    delivery_to_date=combo_item.delivery_to_date,
                    quantity=combo_item.quantity,
                    preferences=combo_item.preferences,
                    price_snapshot=combo.price,
                    combo_items_snapshot=combo_items_snapshot
                )

            # Calculate pricing
            order.calculate_pricing()
            
            # Delete ordered items from cart
            cart_items.delete()
            combo_items.delete()

            order_serializer = OrderSerializer(order, context={'request': request})

            return Response(order_serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class OrderDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk, user):
        return get_object_or_404(Order, pk=pk, user=user)

    def get(self, request, pk):
        order = self.get_object(pk, request.user)
        serializer = OrderSerializer(order)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, pk):
        order = self.get_object(pk, user=self.request.user)

        if 'status' in request.data:
            new_status = request.data['status']

            if new_status == 'CANCELLED':
                if order.status in ['PENDING', 'PROCESSING']:
                    order.status = 'CANCELLED'
                    order.save()
                    serializer = OrderSerializer(order)
                    return Response(serializer.data, status=status.HTTP_200_OK)
                else:
                    return Response(
                        {"error": "Cannot cancel order in current status"}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
            else:
                return Response(
                    {"error": "Only cancellation is allowed for users"}, 
                    status=status.HTTP_403_FORBIDDEN
                )

        if 'payment_status' in request.data and request.user.is_staff:
            order.payment_status = request.data['payment_status']
            order.save()

        serializer = OrderSerializer(order)
        return Response(serializer.data, status=status.HTTP_200_OK)


class OrderCancelView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk, user=request.user)

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