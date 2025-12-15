from rest_framework import serializers
from .models import Notification

class NotificationSerializer(serializers.ModelSerializer):

    class Meta:
        model = Notification
        fields = ['nid', 'notification', 'user', 'is_read']
        read_only_fields = ['nid', 'notification', 'user', 'is_read']

