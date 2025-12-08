from django.urls import path
from .views import UserRegistrationView, UserLoginView, UserLogoutView, UserProfileView, UserSubscriptionView, SubscriptionListView
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path('register/', UserRegistrationView.as_view(), name='register'),
    path('login/', UserLoginView.as_view(), name='login'),
    path('logout/', UserLogoutView.as_view(), name='logout'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('profile/', UserProfileView.as_view(), name='profile'),
    path('subscriptions/', SubscriptionListView.as_view(), name='subscription-list'),
    path('subscription/', UserSubscriptionView.as_view(), name='user-subscription'),
]