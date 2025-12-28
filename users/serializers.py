from rest_framework import serializers
from django.contrib.auth import authenticate
from django.core.mail import send_mail
from django.utils.timezone import now, timedelta
from .models import CustomUser, Subscription, UserSubscription
from django.conf import settings
import random, secrets
from django.utils import timezone
from django.core.cache import cache


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = CustomUser
        fields = ['phone_number', 'email', 'password', 'confirm_password', 'user_type', 'no_of_peoples']

    def validate_phone_number(self, value):
        if CustomUser.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError("Phone number already registered")
        return value

    def validate_email(self, value):
        if CustomUser.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already registered")
        return value

    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match"})
        return data

    def create(self, validated_data):
        validated_data.pop('confirm_password')
        user = CustomUser.objects.create_user(
            **validated_data,
            is_active=False
        )
        return user


class UserLoginSerializer(serializers.Serializer):
    phone_number = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        phone_number = data.get('phone_number')
        password = data.get('password')
        
        if not phone_number or not password:
            raise serializers.ValidationError('Must include "phone_number" and "password"')

        try:
            user = CustomUser.objects.get(phone_number=phone_number)
        except CustomUser.DoesNotExist:
            raise serializers.ValidationError('Invalid phone number or password')
        
        if not user.is_active:
            if not user.check_password(password):
                raise serializers.ValidationError('Invalid phone number or password')
            
            otp = str(random.randint(100000, 999999))
            flow_key = user.email
            request = self.context.get('request')
            request.session['email'] = flow_key
            
            cache.set(
                f"otp_flow:{flow_key}",
                {
                    "user_id": user.id,
                    "otp_type": "activate",
                    "otp": otp,
                    "created_at": timezone.now().isoformat()
                },
                timeout=300
            )
            
            send_mail(
                'Account activation OTP',
                f'Your OTP code is {otp}',
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False
            )
            
            return False 
        
        authenticated_user = authenticate(phone_number=phone_number, password=password)
        
        if not authenticated_user:
            raise serializers.ValidationError('Invalid phone number or password')
        
        authenticated_user.last_login = timezone.now()
        authenticated_user.save()
        
        return authenticated_user


class SubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = ['sid', 'subscription', 'rate', 'duration_days']
        read_only_fields = ['sid']


class UserSubscriptionSerializer(serializers.ModelSerializer):
    plan_details = SubscriptionSerializer(source='plan', read_only=True)
    days_remaining = serializers.SerializerMethodField()
    is_expired = serializers.SerializerMethodField()
    
    class Meta:
        model = UserSubscription
        fields = [
            'sub_id', 'plan', 'plan_details', 'activated_from', 
            'expires_on', 'is_active', 'days_remaining', 'is_expired',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['sub_id', 'created_at', 'updated_at', 'expires_on']
    
    def get_days_remaining(self, obj):
        if obj.expires_on:
            delta = obj.expires_on - timezone.now().date()
            return max(0, delta.days)
        return 0
    
    def get_is_expired(self, obj):
        if obj.expires_on:
            return obj.expires_on < timezone.now().date()
        return True


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = [
            'id', 'phone_number', 'email', 'first_name', 'last_name', 'organization_name', 'image',
            'user_type', 'no_of_peoples', 'payment_method', 'street_address',
            'city', 'status', 'meal_preferences', 'is_active', 
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'status', 'phone_number']

    def validate_payment_method(self, value):
        if value:
            valid_methods = [choice[0] for choice in CustomUser.PAYMENT_METHOD]
            if value not in valid_methods:
                raise serializers.ValidationError(
                    f"Invalid payment method. Choose from: {', '.join(valid_methods)}"
                )
        return value

    def validate(self, data):
        instance = self.instance
        user_type = data.get(
            'user_type',
            instance.user_type if instance else None
        )
        organization_name = data.get(
            'organization_name',
            instance.organization_name if instance else None
        )
        first_name = data.get(
            'first_name',
            instance.first_name if instance else None
        )
        last_name = data.get(
            'last_name',
            instance.last_name if instance else None
        )
        
        if user_type == "ORGANIZATIONS" and not organization_name:
            raise serializers.ValidationError(
                {"organization_name": "Organization name is required for organizations"}
            )

        if user_type == "INDIVIDUALS" and not (first_name and last_name):
            raise serializers.ValidationError(
                {"first_name": "First and last name are required for individuals"}
            )

        return data


class OTPSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False)
    otp = serializers.CharField(required=True)

    def validate(self, data):
        request = self.context.get('request')
        email = data.get('email')
        otp_input = data.get('otp')
        
        if not email:
            raise serializers.ValidationError("Email is required")
        
        if not otp_input:
            raise serializers.ValidationError("OTP is required")

        cache_key = f"otp_flow:{email}"
        cached_data = cache.get(cache_key)

        if not cached_data:
            raise serializers.ValidationError("OTP expired or not found")

        if cached_data['otp'] != otp_input:
            raise serializers.ValidationError("Invalid OTP")
        
        cache.delete(cache_key)
        
        data['verified'] = True
        data['user_id'] = cached_data['user_id']
        data['otp_type'] = cached_data['otp_type']
        
        return data


class ResetPasswordRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        try:
            user = CustomUser.objects.get(email=value)
        except CustomUser.DoesNotExist:
            raise serializers.ValidationError("User with this email does not exist.")
        
        otp = str(random.randint(100000, 999999))

        request = self.context.get('request')
        flow_key = value
        request.session['email'] = value
        
        cache.set(
            f"otp_flow:{flow_key}",
            {
                "user_id": user.id,
                "otp_type": "reset_password",
                "otp": otp,
                "created_at": timezone.now().isoformat()
            },
            timeout=300
        )

        send_mail(
            'Reset Password OTP',
            f'Your OTP code is {otp}',
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False
        )
        
        self.user_id = user.id
        self.flow_key = flow_key
        return value


class ResetPasswordSerializer(serializers.Serializer):
    new_password = serializers.CharField(min_length=8, write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, data):
        new_password = data.get('new_password')
        confirm_password = data.get('confirm_password')

        if not new_password or not confirm_password:
            raise serializers.ValidationError("Both password fields are required.")

        if new_password != confirm_password:
            raise serializers.ValidationError("Password fields must match.")

        return data
    
    