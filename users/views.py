# users/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from django.utils import timezone
from datetime import timedelta
from .models import CustomUser, UserSubscription, Subscription
from .serializers import (
    SubscriptionSerializer, 
    UserSerializer, 
    UserLoginSerializer, 
    UserRegistrationSerializer, 
    UserSubscriptionSerializer
)


def get_tokens_for_user(user):
    """Generate JWT tokens for user"""
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }


class UserRegistrationView(generics.CreateAPIView):
    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny]

    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        tokens = get_tokens_for_user(user)
        
        return Response({
            'user': UserSerializer(user).data,
            'tokens': tokens,
            'is_admin': user.is_staff,
            'message': 'User registered successfully'
        }, status=status.HTTP_201_CREATED)


class UserLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data
        
        tokens = get_tokens_for_user(user)
        
        return Response({
            'user': UserSerializer(user).data,
            'tokens': tokens,
            'is_admin': user.is_staff,
            'message': 'Login successful'
        }, status=status.HTTP_200_OK)


class UserLogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            return Response({'message': 'Successfully logged out'}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': 'Invalid token'}, status=status.HTTP_400_BAD_REQUEST)


class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        serializer = UserSerializer(user)
        
        # Include subscription info if available
        response_data = serializer.data
        try:
            subscription = UserSubscription.objects.get(user=user)
            response_data['subscription'] = UserSubscriptionSerializer(subscription).data
        except UserSubscription.DoesNotExist:
            response_data['subscription'] = None
            
        return Response(response_data, status=status.HTTP_200_OK)

    def put(self, request):
        user = request.user
        serializer = UserSerializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({
            'user': serializer.data,
            'message': 'Profile updated successfully'
        }, status=status.HTTP_200_OK)


class SubscriptionListView(APIView):
    """List all available subscription plans"""
    permission_classes = [AllowAny]
    
    def get(self, request):
        subscriptions = Subscription.objects.all()
        serializer = SubscriptionSerializer(subscriptions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class UserSubscriptionView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get user's subscription details"""
        try:
            subscription = UserSubscription.objects.get(user=request.user)
            serializer = UserSubscriptionSerializer(subscription)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except UserSubscription.DoesNotExist:
            return Response({
                'message': 'No active subscription found. Please subscribe to a plan.'
            }, status=status.HTTP_404_NOT_FOUND)
    
    def post(self, request):
        data = request.data
        
        try:
            plan = Subscription.objects.get(subscription=data.get('plan'))
        except Subscription.DoesNotExist:
            return Response({
                'error': 'Invalid subscription plan'
            }, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        activated_date = timezone.now().date()  # Ensuring this is a date object
        expires_date = activated_date + timedelta(days=plan.duration_days)
        
        subscription, created = UserSubscription.objects.update_or_create(
            user=user,
            defaults={
                'plan': plan,
                'payment_status': 'PAID',
                'activated_from': activated_date,
                'expires_on': expires_date,
                'is_active': True
            }
        )

        # Update user status
        user.status = "ACTIVE"
        user.save()

        serializer = UserSubscriptionSerializer(subscription)
        return Response({
            'subscription': serializer.data,
            'message': 'Subscription activated successfully' if created else 'Subscription updated successfully'
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
    
    def delete(self, request):
        """Cancel user subscription"""
        try:
            subscription = UserSubscription.objects.get(user=request.user)
            subscription.is_active = False
            subscription.payment_status = 'UNPAID'
            subscription.save()
            
            user = request.user
            user.status = 'EXPIRED'
            user.save()
            
            return Response({
                'message': 'Subscription cancelled successfully'
            }, status=status.HTTP_200_OK)
        except UserSubscription.DoesNotExist:
            return Response({
                'error': 'No active subscription found'
            }, status=status.HTTP_404_NOT_FOUND)
