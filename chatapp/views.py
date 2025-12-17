from rest_framework import status
from rest_framework.response import Response
from .serializers import MessageSerializer, ConversationSerializer
from .models import Message, Conversation
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from .pagination import MessageInfiniteScrollPagination


class ConversationView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        if request.user.is_staff:
            conversations = Conversation.objects.all()
            serializer = ConversationSerializer(conversations, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            conversations = Conversation.objects.filter(user=request.user).first()
            if not conversations:
                return Response("Conversation not started.", status=status.HTTP_400_BAD_REQUEST)
            serializer = ConversationSerializer(conversations)
            return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        if request.user.is_staff:
            return Response("You cannot start a conversation. Can only accept for reply.", status=status.HTTP_403_FORBIDDEN)

        existing_conv = Conversation.objects.filter(user=request.user).first()
        if existing_conv:
            return Response("Your conversation is already present.", status=status.HTTP_400_BAD_REQUEST)
        
        conv = Conversation.objects.create(user=request.user)
        serializer = ConversationSerializer(conv)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class MessageView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, slug):
        conversation = Conversation.objects.filter(slug=slug).first()
        if not conversation:
            return Response("Conversation does not exist", status=status.HTTP_404_NOT_FOUND)

        if not (request.user.is_staff or conversation.user == request.user):
            return Response("You do not have access to this conversation", status=status.HTTP_403_FORBIDDEN)

        messages = Message.objects.filter(conversation=conversation).order_by("-timestamp")
        pagination = MessageInfiniteScrollPagination()
        paginated = pagination.paginate_queryset(messages, request)
        serializer = MessageSerializer(paginated, many=True)
        return pagination.get_paginated_response(serializer.data)



