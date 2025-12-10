from django.urls import path
from .views import (
    CartListView,
    CartItemDetailView,
    OrderListView,
    OrderDetailView,
    OrderCancelView
)

urlpatterns = [
    path('cart/', CartListView.as_view(), name='cart-item-list'),
    path('cart/clear/', CartListView.as_view(), name='clear-cart'), 
    path('cart/<int:pk>/', CartItemDetailView.as_view(), name='cart-item-detail'),
    path('orders/', OrderListView.as_view(), name='order-list'),
    path('orders/<int:pk>/', OrderDetailView.as_view(), name='order-detail'),
    path('orders/<int:pk>/cancel/', OrderCancelView.as_view(), name='order-cancel'),
]
