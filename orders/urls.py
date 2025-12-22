from django.urls import path
from .views import (
    CartListView,
    CartItemDetailView,
    CartItemUpdateView,
    OrderListView,
    OrderDetailView,
    OrderCancelView,
    OrderStatusChoicesView,
    OrderCreateView,
    OrderPreviewView
)

app_name = 'orders'

urlpatterns = [
    path('cart/', CartListView.as_view(), name='my-cart'),
    path('cart/preview/', OrderPreviewView.as_view(), name='cart-preview'),
    path('cart/<uuid:pk>/', CartItemDetailView.as_view(), name='cart-item-detail'),
    path('cart/<uuid:pk>/update/', CartItemUpdateView.as_view(), name='cart-item-update'),
    path('orders/', OrderListView.as_view(), name='my-orders'),
    path('orders/create/', OrderCreateView.as_view(), name='create-order'),
    path('orders/<uuid:pk>/', OrderDetailView.as_view(), name='order-detail'),
    path('orders/<uuid:pk>/cancel/', OrderCancelView.as_view(), name='cancel-order'),
    path('choices/', OrderStatusChoicesView.as_view(), name='order-choices'),
]