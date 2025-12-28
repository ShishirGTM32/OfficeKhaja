from rest_framework import serializers
from .models import Conversation, Message
from users.serializers import UserSerializer


class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.SerializerMethodField()
    sender_email = serializers.SerializerMethodField()
    
    class Meta:
        model = Message
        fields = ['mid', 'conversation', 'sender', 'sender_name', 'sender_email', 'message', 'timestamp', 'is_read']
        read_only_fields = ['mid', 'conversation', 'timestamp', 'sender_name', 'sender_email']
    
    def get_sender_name(self, obj):
        if obj.sender:
            name = f"{obj.sender.first_name} {obj.sender.last_name}".strip()
            return name if name else obj.sender.email
        return "Unknown"
    
    def get_sender_email(self, obj):
        return obj.sender.email if obj.sender else ""


class LastMessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.SerializerMethodField()
    sender_id = serializers.IntegerField(source='sender.id', read_only=True)
    
    class Meta:
        model = Message
        fields = ['message', 'sender', 'sender_id', 'sender_name', 'timestamp', 'is_read']
    
    def get_sender_name(self, obj):
        if obj.sender:
            name = f"{obj.sender.first_name} {obj.sender.last_name}".strip()
            return name if name else obj.sender.email
        return "Unknown"


class ConversationSerializer(serializers.ModelSerializer):
    user_details = UserSerializer(source='user', read_only=True)
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.IntegerField(read_only=True, default=0)
    is_online = serializers.BooleanField(read_only=True, default=False)
    
    class Meta:
        model = Conversation
        fields = ['cid', 'user', 'user_details', 'slug', 'created_at', 'last_message', 'unread_count', 'is_online']
        read_only_fields = ['cid', 'created_at', 'slug', 'last_message', 'unread_count', 'is_online']
    
    def get_last_message(self, obj):
        last_msg = Message.objects.filter(conversation=obj).select_related('sender').order_by('-timestamp').first()
        if last_msg:
            return LastMessageSerializer(last_msg).data
        return None