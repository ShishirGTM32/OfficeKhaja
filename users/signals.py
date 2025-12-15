from notifications.models import Notification
from .models import CustomUser, UserSubscription
from django.db.models.signals import post_save
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=CustomUser)
def user_registration_notification(sender, instance, created, **kwargs):
    try:
        if created:
            message = f"Welcome to Office Khaja {instance.email}. Thanks for Registration. Hope you will enjoy the services."
        else:
            message = f"Dear {instance.first_name} {instance.last_name}, you have logged in at {instance.last_login}."

        Notification.objects.create(
            user=instance,
            notification=message
        )

        channel_layer = get_channel_layer()
        if channel_layer:  
            async_to_sync(channel_layer.group_send)(
                f"user_{instance.id}",  
                {
                    "type": "notify", 
                    "message": message
                }
            )
    except Exception as e:
        logger.error(f"Exception in user_registration_notification: {e}")



@receiver(post_save, sender=UserSubscription)
def UserSubscriptionNotification(sender, instance, created, **kwargs):
    try:
        if created:
            message = f"Your Subscription has started from {instance.created_at}. It is active for {instance.days_remaining()} and expires at {instance.expires_on}"
        else:
            if instance.is_active:
                message = f"Your Subscription has been renewed from {instance.created_at}. It is active for {instance.days_remaining()} and expires at {instance.expires_on}"
            else:
                message = f"Your Subscription has expired from {instance.updated_at}. Please feel free to renew the application."
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