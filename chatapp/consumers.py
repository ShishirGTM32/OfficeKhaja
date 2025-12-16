from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from asgiref.sync import sync_to_async
import json
from django.core.cache import cache
from users.models import CustomUser
from .models import Conversation, Message


class ChatConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.user = self.scope.get("user")
        if not self.user or not self.user.is_authenticated:
            await self.close()
            return

        self.slug = self.scope["url_route"]["kwargs"]["conversation_slug"]
        self.conversation = await self.get_conversation_by_slug(self.slug)

        if not self.conversation or not await self.has_access():
            await self.close()
            return

        self.room_name = f"support_{self.conversation.cid}"

        await self.channel_layer.group_add(self.room_name, self.channel_name)
        await self.accept()

        self.counter = ConnectionCounter(self.user.id)
        await self.counter.increment()
        await self.read_messages()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_name, self.channel_name)
        await self.counter.decrement()

    async def receive(self, text_data):
        data = json.loads(text_data)
        text = data.get("text", "").strip()
        if not text:
            return

        message = await self.save_message(text)

        await self.channel_layer.group_send(
            self.room_name,
            {
                "type": "chat.message",
                "message": message.message,
                "sender": message.sender.id,
                "timestamp": message.timestamp.isoformat(),
            }
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            "text": event["message"],
            "sender": event["sender"],
            "timestamp": event["timestamp"],
        }))

    @database_sync_to_async
    def get_conversation_by_slug(self, slug):
        try:
            user_id = int(slug.split("-")[-1])
            user = CustomUser.objects.get(id=user_id)
            return Conversation.objects.filter(user=user).first()
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

    @database_sync_to_async
    def read_messages(self):
        messages = Message.objects.filter(conversation=self.conversation)
        return messages.exclude(
            sender=self.user,
        ).update(is_read=True)


class ConnectionCounter:
    def __init__(self, user_id):
        self.key = f"user:{user_id}:online"

    @sync_to_async
    def increment(self):
        count = cache.get(self.key, 0)
        count += 1
        cache.set(self.key, count)
        return count

    @sync_to_async
    def decrement(self):
        count = cache.get(self.key, 0)
        if count <= 1:
            cache.delete(self.key)
            return 0
        else:
            count -= 1
            cache.set(self.key, count)
            return count

    @sync_to_async
    def get_count(self):
        return cache.get(self.key, 0)

    @sync_to_async
    def is_online(self):
        return cache.get(self.key, 0) > 0