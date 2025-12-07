from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authtoken.models import Token 
from django.contrib.auth import login
from django.utils import timezone
from .models import CustomUser, UserSubscription, Subscription
from .serializers import SubscriptionSerializer, UserSerializer, UserLoginSerializer, UserRegistrationSerializer, UserSubscriptionSerializer
from django.shortcuts import get_object_or_404

class UserRegistrationView(generics.CreateAPIView):
    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny]

    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        token, created = Token.objects.get_or_create(user=user)
        return Response({
            'user': UserSerializer(user).data,
            'token': token.key,
            'is_admin': user.is_staff,
            "created": created
        }, status=status.HTTP_201_CREATED)

class UserLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data

        login(request, user)  
        token, created = Token.objects.get_or_create(user=user)
        
        return Response({
            'user': UserSerializer(user).data,
            'token': token.key,
            'is_admin': user.is_staff,
            'created': created
        })

class UserLogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        request.user.auth_token.delete()
        return Response({'message': 'Successfully logged out'}, status=status.HTTP_200_OK)

class UserProfileView(APIView):
    permission_classes  = [IsAuthenticated]

    def get(self, request):
        user = CustomUser.objects.get(phone_number = request.user.phone_number)
        if user.status == "NOT STARTED":
            return Response("Please complete the subscription plan before")
        serializer = UserSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request):
        user = CustomUser.objects.get(phone_number = request.user.phone_number)
        serializer = UserSerializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_202_ACCEPTED)
        

class UserSubscriptionView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        sub = UserSubscription.objects.filter(user = user_id).first()
        if not sub:
            return Response("Please taks a subscritpion first", status=status.HTTP_404_NOT_FOUND)
        serializer = UserSubscriptionSerializer(sub)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def post(self, request, user_id):
        data = request.data
        try:
            sub = Subscription.objects.get(subscription=data['plan'])
        except Subscription.DoesNotExist:
            return Response("Invalid Subscription Type", status=status.HTTP_400_BAD_REQUEST)

        user = CustomUser.objects.filter(id=user_id).first()
        usub = UserSubscription.objects.create(
            user=user,
            plan=sub,
            payment_status="PAID",
            activated_from=timezone.now()
        )

        user.status = "ACTIVE"
        user.save()

        serializer = UserSubscriptionSerializer(usub)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


