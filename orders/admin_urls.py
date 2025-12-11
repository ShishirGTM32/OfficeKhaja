from django.urls import path
from .admin_views import (
    AdminUserListView, AdminUserDetailView,
    AdminOrderListView, AdminOrderDetailView,
    AdminSubscriptionManagementView, AdminSubscriptionDetailView,
    AdminUserSubscriptionListView, AdminUserSubscriptionDetailView,
    AdminMealAvailabilityView, AdminCustomMealListView,
    AdminCustomMealDetailView, AdminStatisticsView
)

urlpatterns = [
    path('users/', AdminUserListView.as_view(), name='admin-users'),
    path('users/<int:user_id>/', AdminUserDetailView.as_view(), name='admin-user-detail'),
    
    path('orders/', AdminOrderListView.as_view(), name='admin-orders'),
    path('orders/<int:order_id>/', AdminOrderDetailView.as_view(), name='admin-order-detail'),
    
    path('subscriptions/', AdminSubscriptionManagementView.as_view(), name='admin-subscriptions'),
    path('subscriptions/<int:sid>/', AdminSubscriptionDetailView.as_view(), name='admin-subscription-detail'),
    
    path('user-subscriptions/', AdminUserSubscriptionListView.as_view(), name='admin-user-subscriptions'),
    path('user-subscriptions/<int:sub_id>/', AdminUserSubscriptionDetailView.as_view(), name='admin-user-subscription-detail'),
    
    path('meals/<int:meal_id>/availability/', AdminMealAvailabilityView.as_view(), name='admin-meal-availability'),
    
    path('custom-meals/', AdminCustomMealListView.as_view(), name='admin-custom-meals'),
    path('custom-meals/<int:combo_id>/', AdminCustomMealDetailView.as_view(), name='admin-custom-meal-detail'),
    
    path('statistics/', AdminStatisticsView.as_view(), name='admin-statistics'),
]
