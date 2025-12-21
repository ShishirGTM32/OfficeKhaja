import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from asgiref.sync import sync_to_async
from django.core.cache import cache
from users.models import CustomUser
from .models import Conversation, Message
import logging

logger = logging.getLogger(__name__)

try:
    redis_instance = cache.client.get_client(write=True)
except Exception as e:
    logger.error(f"Redis connection error: {e}")
    redis_instance = None


class ConnectionCounter:
    TTL = 300
    
    def __init__(self, user_id, is_staff=False):
        self.user_id = str(user_id)
        self.key = f"user:{self.user_id}:connections"
        self.online_set = "online"
        self.is_staff = is_staff

    @sync_to_async
    def increment(self):
        try:
            count = cache.get(self.key, 0) + 1
            cache.set(self.key, count, timeout=self.TTL)
            
            if redis_instance:
                redis_instance.sadd(self.online_set, self.user_id)
                redis_instance.publish("user_status_channel", json.dumps({
                    "user_id": self.user_id,
                    "status": "online",
                    "is_staff": self.is_staff
                }))
            
            return count
        except Exception as e:
            logger.error(f"Error incrementing connection count: {e}")
            return 1

    @sync_to_async
    def decrement(self):
        try:
            count = cache.get(self.key, 0)
            if count <= 1:
                cache.delete(self.key)
                if redis_instance:
                    redis_instance.srem(self.online_set, self.user_id)
                    redis_instance.publish("user_status_channel", json.dumps({
                        "user_id": self.user_id,
                        "status": "offline",
                        "is_staff": self.is_staff
                    }))
                return 0
            else:
                count -= 1
                cache.set(self.key, count, timeout=self.TTL)
                return count
        except Exception as e:
            logger.error(f"Error decrementing connection count: {e}")
            return 0

    @sync_to_async
    def get_count(self):
        try:
            return cache.get(self.key, 0)
        except Exception as e:
            logger.error(f"Error getting connection count: {e}")
            return 0

    async def is_online(self):
        count = await self.get_count()
        return count > 0


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        try:
            self.user = self.scope.get("user")
            if not self.user or not self.user.is_authenticated:
                logger.warning("Unauthenticated connection attempt")
                await self.close(code=4001)
                return  

            self.cid = self.scope["url_route"]["kwargs"].get("conversation_id")
            if not self.cid:
                logger.warning(f"No conversation_id provided for user {self.user.id}")
                await self.close(code=4002)
                return

            self.conversation = await self.get_conversation_by_id(self.cid)
            if not self.conversation:
                logger.warning(f"Conversation {self.cid} not found")
                await self.close(code=4004)
                return

            has_access = await self.has_access()
            if not has_access:
                logger.warning(f"User {self.user.id} denied access to conversation {self.cid}")
                await self.close(code=4003)
                return

            self.room_name = f"conversation_{self.conversation.cid}"
            await self.channel_layer.group_add(self.room_name, self.channel_name)
            await self.accept()

            self.counter = ConnectionCounter(self.user.id, self.user.is_staff)
            await self.counter.increment()
            await self.set_user_status_online()

            await self.channel_layer.group_send(
                self.room_name,
                {
                    "type": "user_status_update",
                    "user_id": str(self.user.id),
                    "status": "online",
                    "is_staff": self.user.is_staff
                }
            )

            await self.send_online_list()
            await self.send_unread_messages()

            logger.info(f"User {self.user.id} connected to conversation {self.cid}")

        except Exception as e:
            logger.error(f"Error in connect: {e}", exc_info=True)
            await self.close(code=4500)

    async def disconnect(self, close_code):
        try:
            if hasattr(self, "counter") and self.counter:
                count = await self.counter.decrement()
                if count == 0:
                    await self.set_user_status_offline()
                    if hasattr(self, "room_name"):
                        await self.channel_layer.group_send(
                            self.room_name,
                            {
                                "type": "user_status_update",
                                "user_id": str(self.user.id),
                                "status": "offline",
                                "is_staff": self.user.is_staff
                            }
                        )

            if hasattr(self, "room_name") and self.room_name:
                await self.channel_layer.group_discard(self.room_name, self.channel_name)

            logger.info(f"User {self.user.id if hasattr(self, 'user') else 'Unknown'} disconnected with code {close_code}")

        except Exception as e:
            logger.error(f"Error in disconnect: {e}", exc_info=True)

    async def receive(self, text_data):
        if not text_data:
            return

        try:
            data = json.loads(text_data)
            msg_type = data.get("type")

            if msg_type == "chat_message":
                messages = await self.get_unread_messages()
                if messages:
                    await self.handle_read_receipt(data)
                await self.handle_chat_message(data)
            elif msg_type == "read":
                await self.handle_read_receipt(data)
            elif msg_type == "typing":
                await self.handle_typing(data)
            else:
                logger.warning(f"Unknown message type: {msg_type}")

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON received: {e}")
        except Exception as e:
            logger.error(f"Error in receive: {e}", exc_info=True)

    async def handle_chat_message(self, data):
        text = data.get("text", "").strip()
        if not text:
            return

        try:
            message = await self.save_message(text)            
            recipient_id = await self.get_recipient_id()
            recipient_counter = ConnectionCounter(recipient_id, not self.user.is_staff)
            recipient_online = await recipient_counter.is_online()
            sender_details = await self.get_sender_details()

            payload = {
                "message": message.message,
                "message_id": message.mid,
                "sender": str(self.user.id),
                "sender_name": sender_details["name"],
                "sender_email": sender_details["email"],
                "timestamp": message.timestamp.isoformat(),
                "is_read": False,
                "recipient_online": recipient_online
            }
            if recipient_online:
                await self.channel_layer.group_send(self.room_name, {
                    "type": "chat_message_handler",
                    **payload
                })

        except Exception as e:
            logger.error(f"Error handling chat message: {e}", exc_info=True)
            await self.send(text_data=json.dumps({
                "type": "error",
                "message": "Failed to send message"
            }))

    async def handle_read_receipt(self, data):
        try:
            await self.mark_messages_as_read(self.user.id)
            await self.channel_layer.group_send(
                self.room_name,
                {
                    "type": "read_receipt_handler",
                    "user_id": str(self.user.id)
                }
            )
        except Exception as e:
            logger.error(f"Error handling read receipt: {e}", exc_info=True)

    async def handle_typing(self, data):
        try:
            is_typing = data.get("is_typing", False)
            sender_details = await self.get_sender_details()
            
            await self.channel_layer.group_send(
                self.room_name,
                {
                    "type": "typing_indicator",
                    "user_id": str(self.user.id),
                    "sender_name": sender_details["name"],
                    "is_typing": is_typing
                }
            )
        except Exception as e:
            logger.error(f"Error handling typing indicator: {e}", exc_info=True)


    async def chat_message_handler(self, event):
        await self.send(text_data=json.dumps({
            "type": "chat_message",
            "message": event["message"],
            "message_id": event["message_id"],
            "sender": event["sender"],
            "sender_name": event.get("sender_name", ""),
            "timestamp": event["timestamp"],
            "is_read": event.get("is_read", False),
            "recipient_online": event.get("recipient_online")
        }))

    async def read_receipt_handler(self, event):
        user_id = event.get("user_id")
        if user_id != str(self.user.id):
            await self.send(text_data=json.dumps({
                "type": "read_receipt",
                "user_id": user_id
            }))

    async def typing_indicator(self, event):
        user_id = event.get("user_id")
        if user_id != str(self.user.id):
            await self.send(text_data=json.dumps({
                "type": "typing",
                "user_id": user_id,
                "sender_name": event.get("sender_name", ""),
                "is_typing": event.get("is_typing", False)
            }))

    async def user_status_update(self, event):
        await self.send(text_data=json.dumps({
            "type": "user_status",
            "user_id": event["user_id"],
            "status": event["status"],
            "is_staff": event.get("is_staff", False)
        }))

    async def send_online_list(self):
        try:
            if redis_instance:
                online_ids = await sync_to_async(redis_instance.smembers)("online")

                online_ids = [id.decode() if isinstance(id, bytes) else str(id) for id in online_ids]
                users = await self.get_users_by_ids(online_ids)
            else:
                users = []
            await self.send(text_data=json.dumps({
                "type": "online_users",
                "users": [
                    {
                        "id": str(u.id),
                        "name": f"{u.first_name} {u.last_name}",
                        "email": u.email,
                        "is_staff": u.is_staff
                    }
                    for u in users
                ]
            }))
        except Exception as e:
            logger.error(f"Error sending online list: {e}", exc_info=True)

    async def send_unread_messages(self):
        try:
            unread_messages = await self.get_unread_messages()
            for msg in unread_messages:
                sender_info = await self.get_user_info(msg.sender_id)
                await self.send(text_data=json.dumps({
                    "type": "chat_message",
                    "message": msg.message,
                    "message_id": msg.mid,
                    "sender": str(msg.sender_id),
                    "sender_name": sender_info["name"],
                    "sender_email": sender_info["email"],
                    "timestamp": msg.timestamp.isoformat(),
                    "is_read": False,
                    "unread": True
                }))
        except Exception as e:
            logger.error(f"Error sending unread messages: {e}", exc_info=True)

    async def set_user_status_online(self):
        try:
            await sync_to_async(cache.set)(
                f"user:{self.user.id}:status",
                "online",
                timeout=300
            )
        except Exception as e:
            logger.error(f"Error setting online status: {e}", exc_info=True)

    async def set_user_status_offline(self):
        try:
            await sync_to_async(cache.set)(
                f"user:{self.user.id}:status",
                "offline",
                timeout=300
            )
        except Exception as e:
            logger.error(f"Error setting offline status: {e}", exc_info=True)

    @database_sync_to_async
    def get_sender_details(self):
        return {
            "name": f"{self.user.first_name} {self.user.last_name}".strip() or self.user.email,
            "email": self.user.email
        }

    @database_sync_to_async
    def get_user_info(self, user_id):
        try:
            user = CustomUser.objects.get(id=user_id)
            return {
                "name": f"{user.first_name} {user.last_name}".strip() or user.email,
                "email": user.email
            }
        except CustomUser.DoesNotExist:
            return {"name": "Unknown User", "email": ""}

    @database_sync_to_async
    def get_users_by_ids(self, ids):
        if not ids:
            return []
        return list(CustomUser.objects.filter(id__in=ids))

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

    @database_sync_to_async
    def save_message(self, text):
        return Message.objects.create(
            conversation=self.conversation,
            sender=self.user,
            message=text,
            is_read=False
        )

    @database_sync_to_async
    def get_recipient_id(self):
        if self.user.is_staff:
            return self.conversation.user.id
        staff = CustomUser.objects.filter(is_staff=True).first()
        return staff.id if staff else None

    @database_sync_to_async
    def mark_messages_as_read(self, user_id):
        Message.objects.filter(
            conversation=self.conversation,
            is_read=False
        ).exclude(
            sender_id=user_id
        ).update(is_read=True)

    @database_sync_to_async
    def get_conversation_by_id(self, cid):
        try:
            return Conversation.objects.get(cid=cid)
        except Conversation.DoesNotExist:
            return None

    @database_sync_to_async
    def has_access(self):
        return self.user.is_staff or self.user == self.conversation.user