from notifications.models import Notification
from .models import CustomUser
from django.db.models.signals import post_save
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

@receiver(post_save, sender=CustomUser)
def UserRegistratonNotification(sender, instance, created, **kwargs):
    try:
        if created:
            message = f"Welcome to Office Khaja {instance.email}. Thanks for Registration. Hope you will enjoy the services"
        Notification.objects.create(
            user=instance,
            notification = message
        )

        channel = get_channel_layer()
        async_to_sync(channel.group_send)(
            f"user_{instance.id}",
            {
                "type": "notify",
                "notification": message
            }
        )
    except Exception as e:
        print(f"an exception occured. {e}")