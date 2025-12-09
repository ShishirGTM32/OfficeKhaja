from rest_framework import serializers
from django.contrib.auth import authenticate
from django.core.mail import send_mail
from django.utils.timezone import now, timedelta
from .models import CustomUser, Subscription, UserSubscription
from django.conf import settings
import random
from django.utils import timezone


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = CustomUser
        fields = [
            'phone_number', 'email', 'password', 
            'confirm_password', 'user_type', 'no_of_peoples'
        ]

    def validate_phone_number(self, value):
        if CustomUser.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError("Phone number already registered")
        return value
    
    def validate_email(self, value):
        if CustomUser.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already registered")
        return value

    def validate_payment_method(self, value):
        valid_methods = [choice[0] for choice in CustomUser.PAYMENT_METHOD]
        if value not in valid_methods:
            raise serializers.ValidationError(
                f"Invalid payment method. Choose from: {', '.join(valid_methods)}"
            )
        return value

    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match"})
        return data

    def create(self, validated_data):
        validated_data.pop('confirm_password')
        user = CustomUser.objects.create_user(**validated_data, is_active=False)
        otp = str(random.randint(100000, 999999))

        request = self.context.get("request")
        if not request:
            raise RuntimeError("Request must be passed in serializer context.")
        request.session['otp'] = otp
        request.session['otp_created_at'] = timezone.now().isoformat()
        request.session['otp_type'] = 'register'
        request.session['register_user_id'] = user.id
        send_mail(
            'Registration Confirmation OTP',
            f'Your OTP code is {otp}.',
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False
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
            if not user:
                raise serializers.ValidationError('Invalid phone number or password')
            if not user.is_active:
                raise serializers.ValidationError('User account is disabled')
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
    otp = serializers.CharField()
    otp_type = serializers.ChoiceField(choices=['register', 'reset_password'])

    def validate(self, data):
        request = self.context.get('request')
        if not request:
            raise RuntimeError("Request context required")

        otp_type = data.get('otp_type')
        session_type = request.session.get('otp_type')
        print(request.session.get('otp'))

        if session_type != otp_type:
            raise serializers.ValidationError("OTP type mismatch")

        stored_otp = request.session.get('otp')
        created_at = request.session.get('otp_created_at')

        if not stored_otp or not created_at:
            raise serializers.ValidationError("No OTP found. Please request a new one.")

        otp_created_at = timezone.datetime.fromisoformat(created_at)
        if timezone.now() > otp_created_at + timedelta(minutes=10):
            request.session.pop('otp', None)
            request.session.pop('otp_created_at', None)
            request.session.pop('otp_type', None)
            raise serializers.ValidationError("OTP expired. Please request another one.")

        if data['otp'] == stored_otp:
            request.session['otp_verified'] = True

            data['user_id'] = request.session.get('register_user_id') if otp_type == 'register' else request.session.get('reset_user_id')
            request.session.pop('otp', None)
            request.session.pop('otp_created_at', None)
            request.session.pop('otp_type', None)
        else:
            raise serializers.ValidationError("Invalid OTP")

        return data


class ResetPasswordRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        user = CustomUser.objects.filter(email=value).first()
        if not user:
            raise serializers.ValidationError(
                "Requested user email not available. Please check the email."
            )
        otp = str(random.randint(100000, 999999))

        request = self.context.get("request")
        if not request:
            raise RuntimeError("Request must be passed in serializer context.")
        request.session['otp'] = otp
        request.session['otp_created_at'] = timezone.now().isoformat()
        request.session['otp_type'] = 'reset_password'
        request.session['reset_user_id'] = user.id
        send_mail(
            'Password reset OTP',
            f'Your OTP code is {otp}.',
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False
        )

        return value

            

class ResetPasswordSerializer(serializers.Serializer):
    new_password = serializers.CharField()
    confirm_password = serializers.CharField()

    class ResetPasswordSerializer(serializers.Serializer):
        new_password = serializers.CharField()
        confirm_password = serializers.CharField()

        def validate(self, data):
            pass1 = data.get('new_password')
            pass2 = data.get('confirm_password')

            if pass1 != pass2:
                raise serializers.ValidationError("Password fields must match.")

            return data

