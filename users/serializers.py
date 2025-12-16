from rest_framework import serializers
from django.contrib.auth import authenticate
from django.core.mail import send_mail
from django.utils.timezone import now, timedelta
from .models import CustomUser, Subscription, UserSubscription
from django.conf import settings
import random
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

        if phone_number and password:
            user = authenticate(phone_number=phone_number, password=password)
            user.last_login = timezone.now()
            if not user:
                raise serializers.ValidationError('Invalid phone number or password')
            if not user.is_active:
                raise serializers.ValidationError('User account is not active')
            user.save()
            return user
        raise serializers.ValidationError('Must include "phone_number" and "password"')


class SubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = ['sid', 'subscription', 'rate', 'duration_days']
        read_only_fields = ['sid']


class UserSubscriptionSerializer(serializers.ModelSerializer):
    plan_details = SubscriptionSerializer(source='plan', read_only=True)
    days_remaining = serializers.IntegerField(read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = UserSubscription
        fields = [
            'sub_id', 'plan', 'plan_details', 'activated_from', 
            'expires_on', 'is_active', 'days_remaining', 'is_expired',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['sub_id', 'created_at', 'updated_at', 'expires_on']


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = [
            'id', 'phone_number', 'email', 'first_name', 'last_name', 'image',
            'user_type', 'no_of_peoples', 'payment_method', 'street_address',
            'city', 'status', 'meal_preferences', 'is_active', 
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'status', 'phone_number']

    def validate_payment_method(self, value):
        valid_methods = [choice[0] for choice in CustomUser.PAYMENT_METHOD]
        if value not in valid_methods:
            raise serializers.ValidationError(
                f"Invalid payment method. Choose from: {', '.join(valid_methods)}"
            )
        return value

class OTPSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    otp = serializers.CharField()
    otp_type = serializers.ChoiceField(choices=['register', 'reset_password'])

    def validate(self, data):
        user_id = data['user_id']
        otp_type = data['otp_type']
        otp_input = data['otp']

        cache_key = f"otp:{otp_type}:{user_id}"
        cached_data = cache.get(cache_key)
        if not cached_data:
            raise serializers.ValidationError("OTP expired or not found")
        if cached_data['otp'] != otp_input:
            raise serializers.ValidationError("Invalid OTP")
        cache.delete(cache_key)
        data['verified'] = True
        return data

class ResetPasswordRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        user = CustomUser.objects.filter(email=value).first()
        if not user:
            raise serializers.ValidationError("Requested user email not found.")
        otp = str(random.randint(100000, 999999))
        cache_key = f"otp:reset_password:{user.id}"
        cache.set(
            cache_key,
            {"otp": otp, "created_at": timezone.now().isoformat()},
            timeout=300
        )
        from django.core.mail import send_mail
        from django.conf import settings
        send_mail(
            'Reset Password OTP',
            f'Your OTP code is {otp}',
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False
        )
        self.user_id = user.id
        return value


class ResetPasswordSerializer(serializers.Serializer):
    new_password = serializers.CharField()
    confirm_password = serializers.CharField()

    def validate(self, data):
        pass1 = data.get('new_password')
        pass2 = data.get('confirm_password')

        if pass1 != pass2:
            raise serializers.ValidationError("Password fields must match.")

        return data

