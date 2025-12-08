from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
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
            return Response(
                {'message': 'Successfully logged out'}, 
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {'error': 'Invalid token'}, 
                status=status.HTTP_400_BAD_REQUEST
            )


class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        serializer = UserSerializer(user)
        response_data = serializer.data
        
        try:
            subscription = UserSubscription.objects.get(user=user)
            response_data['subscription'] = UserSubscriptionSerializer(subscription).data
        except UserSubscription.DoesNotExist:
            response_data['subscription'] = None
            response_data['message'] = "No active subscription. Please subscribe to a plan."
            
        return Response(response_data, status=status.HTTP_200_OK)

    def put(self, request):
        user = request.user
        payment_method = request.data.get('payment_method')
        if payment_method:
            valid_methods = [choice[0] for choice in CustomUser.PAYMENT_METHOD]
            if payment_method not in valid_methods:
                return Response({
                    'error': f'Invalid payment method. Choose from: {", ".join(valid_methods)}'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = UserSerializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response({
            'user': serializer.data,
            'message': 'Profile updated successfully'
        }, status=status.HTTP_200_OK)


class SubscriptionListView(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request):
        subscriptions = Subscription.objects.all()
        serializer = SubscriptionSerializer(subscriptions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class UserSubscriptionView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            subscription = UserSubscription.objects.get(user=request.user)
            
            if subscription.expires_on < timezone.now().date():
                subscription.is_active = False
                subscription.payment_status = 'UNPAID'
                subscription.save()
                
                user = request.user
                user.status = 'EXPIRED'
                user.save()
            
            serializer = UserSubscriptionSerializer(subscription)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except UserSubscription.DoesNotExist:
            return Response({
                'message': 'No active subscription found. Please subscribe to a plan.'
            }, status=status.HTTP_404_NOT_FOUND)
    
    def post(self, request):
        plan_type = request.data.get('plan')
        
        if not plan_type:
            return Response({
                'error': 'Plan type is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            plan = Subscription.objects.get(subscription=plan_type.upper())
        except Subscription.DoesNotExist:
            valid_plans = [choice[0] for choice in Subscription.SUBSCRIPTION_TYPE]
            return Response({
                'error': f'Invalid subscription plan. Choose from: {", ".join(valid_plans)}'
            }, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        activated_date = timezone.now().date()
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
        message = 'Subscription activated successfully' if created else 'Subscription renewed successfully'
        
        return Response({
            'subscription': serializer.data,
            'message': message
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
    
    def delete(self, request):
        try:
            subscription = UserSubscription.objects.get(user=request.user)
            from orders.models import Order
            active_orders = Order.objects.filter(
                user=request.user,
                status__in=['PENDING', 'PROCESSING', 'DELIVERING']
            ).exists()
            
            if active_orders:
                return Response({
                    'error': 'Cannot cancel subscription with active orders. Please wait for orders to complete.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
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
            }, status=status.HTTP_404_NOT_FOUND
        )