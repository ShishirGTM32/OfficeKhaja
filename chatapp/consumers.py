from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from asgiref.sync import sync_to_async
import json
from django.core.cache import cache
from users.models import CustomUser
from .models import Conversation, Message


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.counter = None
        self.room_name = None

        self.user = self.scope.get("user")
        if not self.user or not self.user.is_authenticated:
            await self.close()
            return

        self.id = self.scope["url_route"]["kwargs"].get("conversation_id")
        if not self.id:
            await self.close()
            return

        self.conversation = await self.get_conversation_by_id(self.id)
        if not self.conversation or not await self.has_access():
            await self.close()
            return

        self.room_name = f"support_{self.conversation.cid}"

        await self.channel_layer.group_add(self.room_name, self.channel_name)
        await self.accept()

        self.counter = ConnectionCounter(self.user.id)
        await self.counter.increment()
        online_count = await self.counter.get_count()
        print(online_count)
        if online_count >=1:
            await self.set_user_status_online()
        unread_messages = await self.get_unread_messages()

        for message in unread_messages:
            await self.send(text_data=json.dumps({
                "type": "chat_message",
                "text": message.message,
                "sender": message.sender_id,
                "timestamp": message.timestamp.isoformat(),
                "unread": True
            }))


    async def disconnect(self, close_code):
        if hasattr(self, "counter") and self.counter:
            await self.counter.decrement()
            count = await self.counter.get_count()  
            if count < 1:
                await self.set_user_status_offline()
        if hasattr(self, "room_name") and self.room_name:
            await self.channel_layer.group_discard(self.room_name, self.channel_name)

    @database_sync_to_async
    def get_unread_messages(self):
        return list(
            Message.objects.filter(
                conversation=self.conversation,
                is_read=False
            )
            .exclude(sender=self.user)
            .order_by("timestamp")
        )

    async def receive(self, text_data):
        if not text_data:
            return

        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return

        msg_type = data.get("type")
        text = data.get("text", "").strip()

        if msg_type == "chat_message" and text:
            message = await self.save_message(text)
            recipient_id = await self.get_recipient_id()
            recipient_online = await ConnectionCounter(recipient_id).is_online()
            payload = {
                "type": "chat_message",
                "message": message.message,
                "sender": self.user.id,
                "timestamp": message.timestamp.isoformat(),
                "delivered": recipient_online,
            }
            if recipient_online:
                await self.channel_layer.group_send(self.room_name, payload)

        elif msg_type == "read":
            await self.channel_layer.group_send(
                self.room_name,
                {
                    "type": "read_messages",
                    "user": self.user.id
                }
            )


    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            "text": event["message"],
            "sender": event["sender"],
            "timestamp": event["timestamp"],
        }))

    async def read_messages(self, event):
        user_id = event.get('user')
        if user_id:
            await self.mark_messages_as_read(user_id)

    @database_sync_to_async
    def get_recipient_id(self):
        staff = CustomUser.objects.filter(is_staff=True).first()
        return self.conversation.user.id if self.user.is_staff else staff.id



    @database_sync_to_async
    def mark_messages_as_read(self, user_id):
        messages = Message.objects.filter(conversation=self.conversation)
        return messages.exclude(sender_id=user_id).update(is_read=True)

    @database_sync_to_async
    def get_conversation_by_id(self, id):
        try:
            return Conversation.objects.filter(cid=id).first()
        except (CustomUser.DoesNotExist, ValueError, IndexError):
            return None

    @database_sync_to_async
    def has_access(self):
        return self.user.is_staff or self.user == self.conversation.user

    @database_sync_to_async
    def save_message(self, text):
        return Message.objects.create(
            conversation=self.conversation,
            sender=self.user,
            message=text
        )

    async def set_user_status_online(self):
        cache.set(f"user:{self.user.id}:status", "online")

    async def set_user_status_offline(self):
        cache.set(f"user:{self.user.id}:status", "offline")


class ConnectionCounter:

    TTL = 60 

    def __init__(self, user_id):
        self.key = f"user:{user_id}:online"

    @sync_to_async
    def increment(self):
        count = cache.get(self.key, 0)
        count += 1
        cache.set(self.key, count, timeout=self.TTL) 
        return count

    @sync_to_async
    def refresh_ttl(self):
        count = cache.get(self.key, 0)
        if count > 0:
            cache.set(self.key, count, timeout=self.TTL)
        return count

    @sync_to_async
    def decrement(self):
        count = cache.get(self.key, 0)
        if count <= 1:
            cache.delete(self.key)
            return 0
        else:
            count -= 1
            cache.set(self.key, count, timeout=self.TTL) 
            return count

    @sync_to_async
    def get_count(self):
        return cache.get(self.key, 0)
    
    async def is_online(self):
        return await self.get_count() > 0
