from rest_framework import serializers
from .models import Conversation, Message
from users.models import CustomUser

class ConversationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Conversation
        fields = ['cid', 'user', 'slug', 'created_at']
        read_only_fields = ['cid', 'created_at', 'slug']

class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.SerializerMethodField()
    class Meta:
        model = Message
        fields = ['mid', 'conversation', 'sender', 'sender_name', 'message', 'timestamp']
        read_only_fields = ['mid', 'conversation', 'timestamp', 'sender_name']
    
    def get_sender_name(self, obj):
        return f"{obj.sender.first_name} {obj.sender.last_name}" if obj.sender else None