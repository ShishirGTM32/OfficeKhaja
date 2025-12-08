from django.urls import path
from .views import (
    CartView,
    CartItemListView,
    CartItemDetailView,
    OrderListView,
    OrderDetailView,
    OrderCancelView
)

urlpatterns = [
    path('cart/', CartView.as_view(), name='cart'),
    path('cart/clear/', CartView.as_view(), name='clear-cart'), 
    
    path('cart/items/', CartItemListView.as_view(), name='cart-item-list'),
    path('cart/items/<int:pk>/', CartItemDetailView.as_view(), name='cart-item-detail'),
    
    path('orders/', OrderListView.as_view(), name='order-list'),
    path('orders/<int:pk>/', OrderDetailView.as_view(), name='order-detail'),
    path('orders/<int:pk>/cancel/', OrderCancelView.as_view(), name='order-cancel'),
]
