from django.urls import path
from .staff_views import (
    StaffOrderListView, StaffOrderDetailView,
     StaffComboOrderItemListView,
    StaffComboOrderItemDetailView, StaffSendDeliveryReminderView,
    StaffMealAvailabilityView, StaffDeliveryScheduleView
)

urlpatterns = [
    path('orders/', StaffOrderListView.as_view(), name='staff-orders'),
    path('orders/<int:order_id>/', StaffOrderDetailView.as_view(), name='staff-order-detail'),
    
    path('combo-orders/', StaffComboOrderItemListView.as_view(), name='staff-combo-orders'),
    path('combo-orders/<int:item_id>/', StaffComboOrderItemDetailView.as_view(), name='staff-combo-order-detail'),
    
    path('send-delivery-reminders/', StaffSendDeliveryReminderView.as_view(), name='staff-send-reminders'),
    
    path('meals/<int:meal_id>/availability/', StaffMealAvailabilityView.as_view(), name='staff-meal-availability'),
    
    path('delivery-schedule/', StaffDeliveryScheduleView.as_view(), name='staff-delivery-schedule'),
]
