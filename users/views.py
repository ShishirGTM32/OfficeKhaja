from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone
from datetime import timedelta
from .models import CustomUser, UserSubscription, Subscription
import random
from django.core.mail import send_mail
from django.conf import settings
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


class UserRegistrationView(generics.CreateAPIView):
    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny]

    def create(self, request):
        serializer = self.get_serializer(data=request.data, context = {"request":request})
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
                'activated_from': activated_date,
                'expires_on': expires_date,
                'is_active': True
            }
        )
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


class ResetPasswordRequestView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ResetPasswordRequestSerializer(data=request.data, context={"request":request})
        serializer.is_valid(raise_exception=True)
        return Response("OTP sent to your mail.", status=status.HTTP_200_OK)
    

class OTPVerificationView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = OTPSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        otp_type = serializer.validated_data['otp_type']
        user_id = serializer.validated_data['user_id']

        if otp_type == 'register' and user_id:
            user = CustomUser.objects.get(id=user_id)
            user.is_active = True
            user.save()
            request.session.pop('register_user_id', None)

            return Response({"detail": "Registration confirmed. Account activated."}, status=status.HTTP_202_ACCEPTED)

        elif otp_type == 'reset_password':
            return Response({"detail": "OTP verified. You can now reset your password."}, status=status.HTTP_202_ACCEPTED)

        return Response({"detail": "OTP verified."}, status=status.HTTP_202_ACCEPTED)


class ResetPasswordView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if request.session.get("otp_verified") is not True:
            return Response({"detail": "OTP not verified."}, status=400)

        user_id = request.session.get("reset_user_id")
        user = CustomUser.objects.get(id=user_id)
        user.set_password(serializer.validated_data["new_password"])
        user.save()
        request.session.pop("otp_verified", None)
        request.session.pop("reset_user_id", None)

        return Response({"detail": "Password reset successful."})

class ResendOTPView(APIView):
    permission_classes=[AllowAny]

    def post(self, request):
        otp_type = request.session['otp_type']

        if otp_type == 'register':
            user_id = request.session.get('register_user_id')
        elif otp_type == 'reset_password':
            user_id = request.session.get('reset_user_id')
        else:
            return Response({"error": "Invalid otp_type"}, status=400)

        if not user_id:
            return Response({"error": "No OTP session found. Please request a new OTP flow."}, status=400)

        new_otp = str(random.randint(100000, 999999))
        request.session['otp'] = new_otp
        request.session['otp_created_at'] = timezone.now().isoformat()
        request.session['otp_type'] = otp_type

        try:
            user = CustomUser.objects.get(id=user_id)
        except CustomUser.DoesNotExist:
            return Response({"error": "User not found"}, status=404)
        
        send_mail(
            'New OTP',
            f'Your OTP code is {new_otp}.',
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False
        )

        return Response({"detail": f"{otp_type.capitalize()} OTP resent successfully"}, status=200)