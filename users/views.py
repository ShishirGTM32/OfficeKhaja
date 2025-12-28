from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from django.utils import timezone
from datetime import timedelta
from .models import CustomUser, UserSubscription, Subscription
from orders.permissions import IsStaff, IsSubscribedUser
import random
from drf_spectacular.utils import extend_schema
from django.core.mail import send_mail
from django.conf import settings
from django.core.cache import cache
from .serializers import (
    SubscriptionSerializer, 
    UserSerializer, 
    UserLoginSerializer, 
    UserRegistrationSerializer, 
    UserSubscriptionSerializer,
    ResetPasswordRequestSerializer,
    OTPSerializer,
    ResetPasswordSerializer
)


def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }


def check_subscription(user):
    if user.is_staff:
        return False  
    
    try:
        subscription = UserSubscription.objects.get(user=user)
    except UserSubscription.DoesNotExist:
        return True
    
    if subscription.expires_on < timezone.now().date():
        subscription.is_active = False
        subscription.save()
        user.status = False
        user.save()
        return True
    
    if not subscription.is_active:
        return True
    
    return False 


@extend_schema(
    request=UserRegistrationSerializer,
    responses={200: UserRegistrationSerializer}
)
class UserRegistrationView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        otp = str(random.randint(100000, 999999))

        flow_key = user.email
        cache.set(
            f"otp_flow:{flow_key}",
            {
                "user_id": user.id,
                "otp_type": "register",
                "otp": otp,
                "created_at": timezone.now().isoformat(),
            },
            timeout=300 
        )
        request.session['email'] = flow_key

        send_mail(
            subject='Registration Confirmation OTP',
            message=f'Your OTP code is {otp}',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False
        )

        tokens = get_tokens_for_user(user)

        return Response({
            'user': UserSerializer(user).data,
            'tokens': tokens,
            'is_admin': user.is_staff,
            'message': 'User registered successfully. OTP sent to email.'
        }, status=status.HTTP_201_CREATED)


@extend_schema(
    request=UserLoginSerializer,
    responses={200: UserLoginSerializer}
)
class UserLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserLoginSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data
        if user is False:
            return Response({
                'message': 'Account not activated. OTP sent to your email.'
            }, status=status.HTTP_403_FORBIDDEN)
        
        if not user:
            return Response({
                'error': 'Invalid credentials'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
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
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response(
                {"error": "Refresh token is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response(
                {"message": "Successfully logged out"},
                status=status.HTTP_200_OK
            )
        except TokenError:
            return Response(
                {"error": "Invalid or expired token"},
                status=status.HTTP_400_BAD_REQUEST
            )


@extend_schema(
    request=UserSerializer,
    responses={200: UserSerializer}
)
class UserProfileView(APIView):
    def get_permissions(self):
        if self.request.method in ['GET', 'PUT']:
            permission_classes = [IsSubscribedUser]
        else:
            permission_classes = [IsStaff]  
        return [permission() for permission in permission_classes]

    def get(self, request):
        user = request.user
        serializer = UserSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)

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


@extend_schema(
    request=SubscriptionSerializer,
    responses={200: SubscriptionSerializer}
)
class SubscriptionListView(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request):
        subscriptions = Subscription.objects.all()
        serializer = SubscriptionSerializer(subscriptions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema(
    request=UserSubscriptionSerializer,
    responses={200: UserSubscriptionSerializer}
)
class UserSubscriptionView(APIView):
    def get_permissions(self):
        if self.request.method in ['GET', 'POST', 'DELETE']:
            permission_classes = [IsAuthenticated]
        else:
            permission_classes = [IsStaff]
        return [permission() for permission in permission_classes]

    def get(self, request):
        try:
            subscription = UserSubscription.objects.get(user=request.user)
        except UserSubscription.DoesNotExist:
            return Response({
                'error': 'You are not subscribed to any plan. Please subscribe.'
            }, status=status.HTTP_404_NOT_FOUND)
        
        if check_subscription(request.user):
            return Response({
                'error': 'Your plan has expired or is not active. Please renew your subscription.',
                'subscription': UserSubscriptionSerializer(subscription).data
            }, status=status.HTTP_403_FORBIDDEN)
        
        serializer = UserSubscriptionSerializer(subscription)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def post(self, request):
        sub = UserSubscription(user=request.user)
        if sub:
            return Response({
                "success":False,
                "message":"Subscription is active. Please perform after expiration."
            }, status=status.HTTP_403_FORBIDDEN)
        plan_type = request.data.get('plan')
        if not plan_type:
            return Response({
                'error': 'Plan type is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            plan = Subscription.objects.get(subscription=plan_type)
        except Subscription.DoesNotExist:
            valid_plans = Subscription.objects.all()
            return Response({
                'error': 'Invalid plan type',
                'available_plans': SubscriptionSerializer(valid_plans, many=True).data
            }, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        activated_date = timezone.now().date()
        expires_date = activated_date + timedelta(days=plan.duration_days)
        
        subscription, created = UserSubscription.objects.update_or_create(
            user=user,
            defaults={
                'plan': plan,
                'activated_from': activated_date,
                'expires_on': expires_date,
                'is_active': True
            }
        )
        
        user.status = True
        user.save()

        serializer = UserSubscriptionSerializer(subscription)
        message = 'Subscription activated successfully' if created else 'Subscription renewed successfully'
        
        return Response({
            'subscription': serializer.data,
            'message': message
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
    
    #need to update the logic and setting up active or not and if new subscription taken look at the old one and based on it update the price regardin the usage.
    def delete(self, request):
        try:
            subscription = UserSubscription.objects.get(user=request.user)
        except UserSubscription.DoesNotExist:
            return Response({
                'error': 'No active subscription found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        from orders.models import Order
        active_orders = Order.objects.filter(
            user=request.user.id,
            status__in=['PENDING', 'PROCESSING', 'DELIVERING']
        ).exists()
        
        if active_orders:
            return Response({
                'error': 'Cannot cancel subscription with active orders. Please wait for orders to complete.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        subscription.is_active = False
        subscription.save()
        
        user = request.user
        user.status = False
        user.save()
        
        return Response({
            'message': 'Subscription cancelled successfully'
        }, status=status.HTTP_200_OK)


@extend_schema(
    request=OTPSerializer,
    responses={200: OTPSerializer}
)
class OTPVerificationView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.session.get('email')
        if not email:
            return Response({
                'error': 'OTP session expired or not found'
            }, status=status.HTTP_400_BAD_REQUEST)

        data = {
            "email": email,
            "otp": request.data.get('otp')
        }

        serializer = OTPSerializer(data=data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        otp_type = serializer.validated_data['otp_type']
        user_id = serializer.validated_data['user_id']

        try:
            user = CustomUser.objects.get(id=user_id)
        except CustomUser.DoesNotExist:
            return Response({
                'error': 'User not found'
            }, status=status.HTTP_404_NOT_FOUND)

        if otp_type in ['register', 'authenticate', 'activate']:
            user.is_active = True
            user.save()
            return Response({
                'detail': 'Account activation completed.'
            }, status=status.HTTP_200_OK)

        elif otp_type == 'reset_password':
            request.session['email'] = email
            return Response({
                'detail': 'OTP verified. You can now reset your password.'
            }, status=status.HTTP_200_OK)

        return Response({
            'error': 'Invalid OTP type'
        }, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    request=ResetPasswordRequestSerializer,
    responses={200: ResetPasswordRequestSerializer}
)
class ResetPasswordRequestView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ResetPasswordRequestSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        return Response({
            'detail': 'Reset password OTP sent to your email.',
            'user_id': serializer.user_id
        }, status=status.HTTP_200_OK)


@extend_schema(
    request=ResetPasswordSerializer,
    responses={200: ResetPasswordSerializer}
)
class ResetPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.session.get('email')
        if not email:
            return Response({
                'error': 'OTP verification required first'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_password = serializer.validated_data['new_password']
        
        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            return Response({
                'error': 'User not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        user.set_password(new_password)
        user.save()

        request.session.pop('email', None)

        return Response({
            'detail': 'Password reset successful.'
        }, status=status.HTTP_200_OK)


class ResendOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        otp_token = request.session.get('email')
        if not otp_token:
            return Response({
                'error': 'OTP session not found. Please start the process again.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        flow_key = f"otp_flow:{otp_token}"
        flow_data = cache.get(flow_key)
        
        if not flow_data:
            return Response({
                'error': 'OTP session expired or invalid'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        user_id = flow_data.get("user_id")
        otp_type = flow_data.get("otp_type")
        
        if otp_type not in ["register", "reset_password", "authenticate", "activate"]:
            return Response({
                'error': 'Invalid OTP flow'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = CustomUser.objects.get(id=user_id)
        except CustomUser.DoesNotExist:
            return Response({
                'error': 'User not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        cache.delete(flow_key)

        otp = str(random.randint(100000, 999999))

        cache.set(
            flow_key,
            {
                "user_id": user.id,
                "otp_type": otp_type,
                "otp": otp,
                "created_at": timezone.now().isoformat()
            },
            timeout=300
        )

        send_mail(
            subject="Your OTP Code",
            message=f"Your OTP code is {otp}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )

        return Response({
            'detail': f"{otp_type.replace('_', ' ').title()} OTP resent successfully"
        }, status=status.HTTP_200_OK)
    
