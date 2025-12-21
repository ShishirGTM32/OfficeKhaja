from rest_framework import status
from rest_framework.response import Response
from .serializers import MessageSerializer, ConversationSerializer
from .models import Message, Conversation
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q, Exists, OuterRef
from .pagination import MessageInfiniteScrollPagination
from users.serializers import UserSerializer


class ConversationView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        if request.user.is_staff:
            conversations = Conversation.objects.filter(
                Exists(Message.objects.filter(conversation=OuterRef('pk')))
            ).select_related('user').order_by('-created_at')
            
            data = []
            for conv in conversations:
                conv_data = ConversationSerializer(conv).data
                conv_data['user_details'] = UserSerializer(conv.user).data
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
            return Response(serializer.data, status=status.HTTP_200_OK)

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

        messages = Message.objects.filter(conversation=conversation)

        search_query = request.query_params.get('search', None)
        if search_query:
            messages = messages.filter(Q(message__icontains=search_query))
        
        messages = messages.order_by("timestamp")
        

        pagination = MessageInfiniteScrollPagination()
        paginated = pagination.paginate_queryset(messages, request)
        serializer = MessageSerializer(paginated, many=True)
        return pagination.get_paginated_response(serializer.data)