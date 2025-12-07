from rest_framework import serializers
from .models import Subscription, CustomUser, UserSubscription
from django.contrib.auth import authenticate

class SubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = ['sid', 'subscription', 'rate']

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id','first_name', 'last_name', 'phone_number','user_type', 'no_of_peoples', 'payment_method', 'street_address', 'city', 'meal_preferences', 'status']

class UserRegistrationSerializer(serializers.ModelSerializer):
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = CustomUser
        fields = [
            'phone_number',
            'password',
            'password_confirm',
            'first_name',
            'last_name',
            'user_type',
            'no_of_peoples'
        ]
        extra_kwargs = {'password': {'write_only': True}}

    def validate(self, data):
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError("Passwords do not match.")
        if data['user_type'] == "ORGANIZATIONS" and data['no_of_peoples'] < 2:
            raise serializers.ValidationError("Organizations must have at least 2 people.")
        if data['user_type'] == "INDIVIDUALS" and data['no_of_peoples'] != 1:
            raise serializers.ValidationError("Individuals must have exactly 1 person.")
        return data

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        user = CustomUser.objects.create_user(**validated_data)
        return user


class UserLoginSerializer(serializers.Serializer):
    phone_number = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = authenticate(
            phone_number=data['phone_number'],  
            password=data['password']
        )
        if not user:
            raise serializers.ValidationError("Invalid credentials")
        return user

class UserSubscriptionSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    plan = SubscriptionSerializer()

    class Meta:
        model = UserSubscription
        fields = ['sub_id', 'user', 'plan', 'activated_from']
        read_only_fields = ['sub_id']