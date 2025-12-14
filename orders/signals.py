from notifications.models import Notification
from .models import Order
from users.models import CustomUser
from django.db.models.signals import post_save
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

@receiver(post_save, sender=Order)
def OrderStatusChangedNotification(sender, instance, created, **kwargs):
    try:
        if created:
            message = f"Your order #{instance.id} has beed created. Time:{instance.created_at}"
        else:
            if instance.status == "PROCESSING":
                message = f"Your order #{instance.id} is being processed. Time:{instance.updated_at}"
            
            if instance.status == "DELIVERING":
                message = f"Your order #{instance.id} is being delivered to you. Time:{instance.updated_at}"

            if instance.status == "DELIVERED":
                message = f"Your order #{instance.id} is delivered. Enjoy your khaja. Time:{instance.updated_at}"
            
            if instance.status == "CANCELLED":
                message = f"Your order #{instance.id} is cancelled. Time:{instance.updated_at}"

        Notification.objects.create(
            user=instance.user,
            notification = message
        )

        channel = get_channel_layer()
        async_to_sync(channel.group_send)(
            f"user_{instance.user.id}",
            {
                "type": "notify",
                "notification": message
            }
        )
    except Exception as e:
        print(f"an exception occured. {e}")

