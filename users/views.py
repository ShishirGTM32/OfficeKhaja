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
import secrets
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
        return True
    subscription = UserSubscription.objects.filter(user=user).first()
    if subscription.expires_on < timezone.now().date():
        subscription.is_active = False
        subscription.save()
        user = user
        user.status = False
        user.save()
        return True
    elif not subscription.is_active:
        return True
    else:
        return False

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

class UserLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserLoginSerializer(data=request.data,
                                         context = {'request':request}
                                         )
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data
        if not user:
            return Response("verify otp before logging in.", status=status.HTTP_401_UNAUTHORIZED)
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
        response_data = serializer.data            
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
    def get_permissions(self):
        if self.request.method in ['GET', 'POST', 'DELETE']:
            permission_classes = [IsAuthenticated]
        else:
            permission_classes = [IsStaff]
        return [permission() for permission in permission_classes]

    def get(self, request):
        subscription = UserSubscription.objects.filter(user=request.user).first()
        if not subscription:
            return Response("You are not subscribed to any plan please subscribe.", status=status.HTTP_403_FORBIDDEN)        
        if check_subscription(request.user):
            return Response("Your plan has expired please renew subscription or subscription not active", status=status.HTTP_200_OK)
        serializer = UserSubscriptionSerializer(subscription)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def post(self, request):
        plan_type = request.data.get('plan')
        if not plan_type:
            return Response({
                'error': 'Plan type is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            plan = Subscription.objects.get(subscription=plan_type)
        except Subscription.DoesNotExist:
            valid = Subscription.objects.all()
            return Response(SubscriptionSerializer(valid).data, status=status.HTTP_400_BAD_REQUEST)

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
    
    def delete(self, request):
        try:
            subscription = UserSubscription.objects.get(user=request.user)
            if not subscription:
                return Response("Subscription not available. Can't cancel.", status=status.HTTP_400_BAD_REQUEST)
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
        except UserSubscription.DoesNotExist:
            return Response({
                'error': 'No active subscription found'
            }, status=status.HTTP_404_NOT_FOUND
        )


class OTPVerificationView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.session['email']
        data= {
            "email":email,
            "otp":request.data.get('otp')
        }
        serializer = OTPSerializer(data=data,
                                   context={'request': request} 
                            )
        serializer.is_valid(raise_exception=True)

        otp_type = serializer.validated_data['otp_type']
        user_id = serializer.validated_data['user_id']

        if otp_type == 'register' or otp_type == 'authenticate':
            user = CustomUser.objects.get(id=user_id)
            user.is_active = True
            user.save()
            del request.session['email']
            return Response({"detail": "Account activation completed."}, status=202)
        elif otp_type == 'reset_password':
            del request.session['email']
            return Response({"detail": "OTP verified. You can now reset your password."}, status=202)


class ResetPasswordRequestView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ResetPasswordRequestSerializer(
            data=request.data,
            context={'request': request}  
        )
        serializer.is_valid(raise_exception=True)
        return Response({
            "detail": "Reset password OTP sent to your email.",
            "user_id": serializer.user_id
        }, status=status.HTTP_200_OK)


class ResetPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = request.session['email']
        new_password = serializer.validated_data['new_password']
        del request.session['email']
        user = CustomUser.objects.get(email=email)
        user.set_password(new_password)
        user.save()

        return Response({"detail": "Password reset successful."}, status=status.HTTP_200_OK)


class ResendOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        otp_token = request.session['email']
        if not otp_token:
            return Response(
                {"error": "OTP token is required"},
                status=400
            )
        flow_key = f"otp_flow:{otp_token}"
        flow_data = cache.get(flow_key)
        if not flow_data:
            return Response(
                {"error": "OTP session expired or invalid"},
                status=400
            )
        user_id = flow_data.get("user_id")
        otp_type = flow_data.get("otp_type")
        if otp_type not in ["register", "reset_password", "authenticate"]:
            return Response(
                {"error": "Invalid OTP flow"},
                status=400
            )
        try:
            user = CustomUser.objects.get(id=user_id)
        except CustomUser.DoesNotExist:
            return Response(
                {"error": "User not found"},
                status=404
            )
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

        return Response(
            {"detail": f"{otp_type.replace('_', ' ').title()} OTP resent successfully"},
            status=200
        )
