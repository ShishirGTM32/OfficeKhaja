from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import CustomUser, Subscription, UserSubscription


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = CustomUser
        fields = [
            'phone_number', 'first_name', 'last_name', 'password', 
            'confirm_password', 'user_type', 'no_of_peoples', 'payment_method'
        ]

    def validate_phone_number(self, value):
        if CustomUser.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError("Phone number already registered")
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
        user = CustomUser.objects.create_user(**validated_data)
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
    days_remaining = serializers.IntegerField(read_only=True, source='days_remaining')
    is_expired = serializers.BooleanField(read_only=True, source='is_expired')
    
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
            'id', 'phone_number', 'first_name', 'last_name', 'image',
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