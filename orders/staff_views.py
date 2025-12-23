from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.http import Http404
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from orders.permissions import IsStaff
from orders.models import Order, ComboOrderItem
from khaja.models import Meals
from users.models import CustomUser
from orders.serializers import OrderSerializer, ComboOrderItemSerializer
from khaja.serializers import MealSerializer
from khaja.pagination import MenuInfiniteScrollPagination


class StaffOrderListView(APIView):
    permission_classes = [IsAuthenticated, IsStaff]

    def get(self, request):
        orders = Order.objects.exclude(status='CANCELLED').order_by('-created_at')
        
        status_filter = request.query_params.get('status')
        today = request.query_params.get('today')
        
        if status_filter:
            orders = orders.filter(status=status_filter.upper())
        
        if today and today.lower() == 'true':
            orders = orders.filter(created_at__date=timezone.now().date())
        
        paginator = MenuInfiniteScrollPagination()
        queryset = paginator.paginate_queryset(orders, request)
        serializer = OrderSerializer(queryset, many=True)
        return paginator.get_paginated_response(serializer.data)


class StaffOrderDetailView(APIView):
    permission_classes = [IsAuthenticated, IsStaff]

    def get(self, request, order_id):
        try:
            order = get_object_or_404(Order, id=order_id)
        except Http404:
            return Response(f"Order with id #{order_id} not found.", status=status.HTTP_404_NOT_FOUND)
        serializer = OrderSerializer(order)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, order_id):
        try:
            order = get_object_or_404(Order, id=order_id)
        except Http404:
            return Response(f"Order with id #{order_id} not found.", status=status.HTTP_404_NOT_FOUND)
        
        new_status = request.data.get('status')
        if not new_status:
            return Response(
                {"error": "status field is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        valid_status = ['PENDING', 'PROCESSING', 'DELIVERING', 'DELIVERED', 'CANCELLED']
        if new_status.upper() not in valid_status:
            return Response(
                {"error": f"Invalid status. Choose from: {', '.join(valid_status)}"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        current_status = order.status
        if current_status == 'DELIVERED':
            return Response(
                {"error": "Cannot change status of delivered order"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if current_status == 'CANCELLED':
            return Response(
                {"error": "Cannot change status of cancelled order"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        old_status = order.status
        order.status = new_status.upper()
        order.save()
        
        try:
            self.send_status_update_email(order, old_status, new_status.upper())
        except Exception as e:
            print(f"Failed to send email: {str(e)}")
        
        serializer = OrderSerializer(order)
        return Response({
            'order': serializer.data,
            'message': f'Order status updated from {old_status} to {new_status.upper()}'
        }, status=status.HTTP_200_OK)

    def send_status_update_email(self, order, old_status, new_status):
        user = order.user
        user = CustomUser.objects.get(phone_number=user.phone_number)
        status_messages = {
            'PROCESSING': 'Your order is being prepared.',
            'DELIVERING': 'Your order is out for delivery!',
            'DELIVERED': 'Your order has been delivered. Enjoy your meal!',
        }
        
        subject = f'Order #{order.id} Status Update - {new_status}'
        message = f"""
            Dear {user.first_name} {user.last_name},

            Your order #{order.id} status has been updated:
            Previous Status: {old_status}
            Current Status: {new_status}

            {status_messages.get(new_status, '')}

            Order Details:
            - Total Amount: Rs. {order.total_price}
            - Delivery Address: {order.delivery_address}

            Thank you for choosing our service!

            Best regards,
            Khaja Team
        """
                    
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
        )


class StaffComboOrderItemListView(APIView):
    permission_classes = [IsAuthenticated, IsStaff]

    def get(self, request):
        combo_items = ComboOrderItem.objects.all().order_by('delivery_from_date')
        
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        today = request.query_params.get('today')
        subscription_plan = request.query_params.get('subscription_plan')
        
        if date_from:
            combo_items = combo_items.filter(delivery_from_date__gte=date_from)
        if date_to:
            combo_items = combo_items.filter(delivery_to_date__lte=date_to)
        if today and today.lower() == 'true':
            today_date = timezone.now().date()
            combo_items = combo_items.filter(
                delivery_from_date__lte=today_date,
                delivery_to_date__gte=today_date
            )
        if subscription_plan:
            combo_items = combo_items.filter(subscription_plan=subscription_plan.upper())
        
        serializer = ComboOrderItemSerializer(combo_items, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class StaffComboOrderItemDetailView(APIView):
    permission_classes = [IsAuthenticated, IsStaff]

    def get(self, request, item_id):
        try:
            combo_item = get_object_or_404(ComboOrderItem, id=item_id)
        except Http404:
            return Response("Combo Item not found with the requested id.", status=status.HTTP_404_NOT_FOUND)
        serializer = ComboOrderItemSerializer(combo_item)
        return Response(serializer.data, status=status.HTTP_200_OK)


class StaffSendDeliveryReminderView(APIView):
    permission_classes = [IsAuthenticated, IsStaff]

    def post(self, request):
        target_date = request.data.get('target_date')
        
        if not target_date:
            target_date = timezone.now().date()
        else:
            try:
                target_date = timezone.datetime.strptime(target_date, '%Y-%m-%d').date()
            except ValueError:
                return Response(
                    {"error": "Invalid date format. Use YYYY-MM-DD"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
        combo_items = ComboOrderItem.objects.filter(
            delivery_from_date__lte=target_date,
            delivery_to_date__gte=target_date,
            order__status__in=['PENDING', 'PROCESSING', 'DELIVERING']
        ).select_related('order', 'combo', 'order__user')
        
        if not combo_items.exists():
            return Response(
                {"message": f"No deliveries scheduled for {target_date}"}, 
                status=status.HTTP_200_OK
            )
        
        sent_count = 0
        failed_count = 0
        
        for combo_item in combo_items:
            try:
                self.send_delivery_reminder_email(combo_item, target_date)
                sent_count += 1
            except Exception as e:
                print(f"Failed to send email for combo item {combo_item.id}: {str(e)}")
                failed_count += 1
        
        return Response({
            'message': f'Delivery reminders sent for {target_date}',
            'sent': sent_count,
            'failed': failed_count,
            'total': combo_items.count()
        }, status=status.HTTP_200_OK)

    def send_delivery_reminder_email(self, combo_item, delivery_date):
        user = combo_item.order.user
        combo = combo_item.combo
        
        meals_list = []
        for meal in combo.meals.meals.all():
            meals_list.append(f"- {meal.name} ({meal.type})")
        
        meals_text = "\n".join(meals_list)
        
        subject = f'Delivery Reminder - Order #{combo_item.order.id}'
        message = f"""
Dear {user.first_name} {user.last_name},

This is a reminder for your scheduled delivery:

Delivery Date: {delivery_date.strftime('%d %B %Y')}
Delivery Time: {combo_item.delivery_time.strftime('%I:%M %p') if combo_item.delivery_time else 'Not specified'}
Subscription Plan: {combo_item.get_subscription_plan_display()}

Meals in your combo:
{meals_text}

Number of Servings: {combo_item.quantity}
Delivery Address: {combo_item.order.delivery_address}

Preferences: {combo_item.preferences if combo_item.preferences else 'None'}

Please ensure someone is available to receive the delivery.

Thank you for choosing our service!

Best regards,
Khaja Team
        """
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False
        )


class StaffMealAvailabilityView(APIView):
    permission_classes = [IsAuthenticated, IsStaff]

    def patch(self, request, meal_id):
        try:
            meal = get_object_or_404(Meals, meal_id=meal_id)
        except Http404:
            return Response("Meal not found with the request id.", status=status.HTTP_404_NOT_FOUND)
        
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
            return Response({
                'meal': serializer.data,
                'message': f"Meal {'enabled' if is_available else 'disabled'} successfully"
            }, status=status.HTTP_200_OK)
        else:
            return Response(
                {"error": "is_available field not found in Meals model. Please add it."}, 
                status=status.HTTP_400_BAD_REQUEST
            )


class StaffDeliveryScheduleView(APIView):
    permission_classes = [IsAuthenticated, IsStaff]

    def get(self, request):
        today = timezone.now().date()
        
        combo_deliveries = ComboOrderItem.objects.filter(
            delivery_from_date__lte=today,
            delivery_to_date__gte=today,
            order__status__in=['PENDING', 'PROCESSING', 'DELIVERING']
        ).select_related('order', 'combo', 'order__user')
        
        regular_orders = Order.objects.filter(
            created_at__date=today,
            status__in=['PENDING', 'PROCESSING', 'DELIVERING']
        ).prefetch_related('order_items', 'order_items__meals')
        
        schedule = {
            'date': today.strftime('%Y-%m-%d'),
            'combo_deliveries': ComboOrderItemSerializer(combo_deliveries, many=True).data,
            'regular_orders': OrderSerializer(regular_orders, many=True).data,
            'total_combo_deliveries': combo_deliveries.count(),
            'total_regular_orders': regular_orders.count()
        }
        
        return Response(schedule, status=status.HTTP_200_OK)