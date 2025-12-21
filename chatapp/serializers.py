from rest_framework import serializers
from .models import Conversation, Message
from users.serializers import UserSerializer


class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Message
        fields = ['mid', 'conversation', 'sender', 'sender_name', 'message', 'timestamp', 'is_read']
        read_only_fields = ['mid', 'conversation', 'timestamp', 'sender_name']
    
    def get_sender_name(self, obj):
        return f"{obj.sender.first_name} {obj.sender.last_name}".strip() if obj.sender else None


class LastMessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Message
        fields = ['message', 'sender', 'sender_name', 'timestamp']
    
    def get_sender_name(self, obj):
        if obj.sender:
            name = f"{obj.sender.first_name} {obj.sender.last_name}".strip()
            return name if name else obj.sender.email
        return "Unknown"


class ConversationSerializer(serializers.ModelSerializer):
    user_details = UserSerializer(source='user', read_only=True)
    last_message = serializers.SerializerMethodField()
    
    class Meta:
        model = Conversation
        fields = ['cid', 'user', 'user_details', 'slug', 'created_at', 'last_message']
        read_only_fields = ['cid', 'created_at', 'slug', 'last_message', 'user']
    
    def get_last_message(self, obj):
        last_msg = Message.objects.filter(conversation=obj).order_by('-timestamp').first()
        if last_msg:
            return LastMessageSerializer(last_msg).data
        return None