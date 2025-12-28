from rest_framework import status
from rest_framework.response import Response
from .serializers import MessageSerializer, ConversationSerializer
from .models import Message, Conversation
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q, Exists, OuterRef, Max, Count, Prefetch
from .pagination import MessageInfiniteScrollPagination
from users.serializers import UserSerializer
from django.core.cache import cache


class ConversationView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        if request.user.is_staff:
            conversations = Conversation.objects.filter(
                Exists(Message.objects.filter(conversation=OuterRef('pk')))
            ).select_related('user').annotate(
                last_message_time=Max('messages__timestamp'),
                unread_count=Count(
                    'messages',
                    filter=Q(messages__is_read=False) & ~Q(messages__sender=request.user)
                )
            ).order_by('-last_message_time') 
            
            data = []
            for conv in conversations:
                conv_data = ConversationSerializer(conv).data
                conv_data['user_details'] = UserSerializer(conv.user).data
                
                # Add online status
                user_status = cache.get(f"user:{conv.user.id}:status", "offline")
                conv_data['is_online'] = (user_status == "online")
                
                # Add unread count
                conv_data['unread_count'] = conv.unread_count
                
                data.append(conv_data)
            
            return Response(data, status=status.HTTP_200_OK)
        else:
            conversation = Conversation.objects.filter(
                user=request.user
            ).filter(
                Exists(Message.objects.filter(conversation=OuterRef('pk')))
            ).first()
            
            if not conversation:
                return Response(
                    {"detail": "No conversation started yet"}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            serializer = ConversationSerializer(conversation)
            response_data = serializer.data
            
            from users.models import CustomUser
            staff_users = CustomUser.objects.filter(is_staff=True)
            is_any_staff_online = False
            for staff in staff_users:
                staff_status = cache.get(f"user:{staff.id}:status", "offline")
                if staff_status == "online":
                    is_any_staff_online = True
                    break
            
            response_data['is_online'] = is_any_staff_online
            
            return Response(response_data, status=status.HTTP_200_OK)

    def post(self, request):
        if request.user.is_staff:
            return Response(
                {"detail": "Staff cannot start conversations. Only users can."}, 
                status=status.HTTP_403_FORBIDDEN
            )

        existing_conv = Conversation.objects.filter(user=request.user).first()
        if existing_conv:
            return Response(
                {"detail": "Your conversation already exists.", "cid": existing_conv.cid}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        conv = Conversation.objects.create(user=request.user)
        serializer = ConversationSerializer(conv)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class MessageView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, uuid):
        conversation = Conversation.objects.filter(cid=uuid).first()
        if not conversation:
            return Response(
                {"detail": "Conversation does not exist"}, 
                status=status.HTTP_404_NOT_FOUND
            )

        if not (request.user.is_staff or conversation.user == request.user):
            return Response(
                {"detail": "You do not have access to this conversation"}, 
                status=status.HTTP_403_FORBIDDEN
            )

        messages = Message.objects.filter(conversation=conversation).select_related('sender')

        search_query = request.query_params.get('search', None)
        if search_query:
            messages = messages.filter(Q(message__icontains=search_query))
        
        messages = messages.order_by("-timestamp")
        
        pagination = MessageInfiniteScrollPagination()
        paginated = pagination.paginate_queryset(messages, request)
        serializer = MessageSerializer(paginated, many=True)
        return pagination.get_paginated_response(serializer.data)