from celery import shared_task
from django.core.cache import cache
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

try:
    redis_instance = cache.client.get_client(write=True)
except Exception as e:
    logger.error(f"Redis connection error: {e}")
    redis_instance = None


@shared_task
def cleanup_stale_connections():
    try:
        if not redis_instance:
            logger.warning("Redis instance not available for cleanup")
            return

        cleaned_users = 0
        cleaned_staff = 0

        online_users = redis_instance.smembers("online_users")
        for user_id_bytes in online_users:
            user_id = user_id_bytes.decode() if isinstance(user_id_bytes, bytes) else str(user_id_bytes)
            connection_key = f"user:{user_id}:connections"
            
            if not cache.get(connection_key):
                redis_instance.srem("online_users", user_id)
                cache.delete(f"user:{user_id}:status")
                cleaned_users += 1
                logger.info(f"Cleaned stale connection for user {user_id}")

        online_staff = redis_instance.smembers("online_staff")
        for staff_id_bytes in online_staff:
            staff_id = staff_id_bytes.decode() if isinstance(staff_id_bytes, bytes) else str(staff_id_bytes)
            connection_key = f"user:{staff_id}:connections"
            
            if not cache.get(connection_key):
                redis_instance.srem("online_staff", staff_id)
                cache.delete(f"user:{staff_id}:status")
                cleaned_staff += 1
                logger.info(f"Cleaned stale connection for staff {staff_id}")

        if cleaned_users > 0 or cleaned_staff > 0:
            logger.info(f"Cleanup completed: {cleaned_users} users, {cleaned_staff} staff members")
        
        return {
            "cleaned_users": cleaned_users,
            "cleaned_staff": cleaned_staff,
            "timestamp": timezone.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error in cleanup_stale_connections: {e}", exc_info=True)
        return {"error": str(e)}


@shared_task
def heartbeat_checker():
    try:
        if not redis_instance:
            return
        current_time = timezone.now().timestamp()
        timeout_threshold = 60 

        for online_set in ["online_users", "online_staff"]:
            online_ids = redis_instance.smembers(online_set)
            
            for user_id_bytes in online_ids:
                user_id = user_id_bytes.decode() if isinstance(user_id_bytes, bytes) else str(user_id_bytes)
                heartbeat_key = f"user:{user_id}:last_heartbeat"
                connection_key = f"user:{user_id}:connections"
                
                last_heartbeat = cache.get(heartbeat_key)
                
                if last_heartbeat is None or (current_time - last_heartbeat) > timeout_threshold:
                    if not cache.get(connection_key):
                        redis_instance.srem(online_set, user_id)
                        cache.delete(f"user:{user_id}:status")
                        cache.delete(heartbeat_key)
                        logger.info(f"Marked user {user_id} as offline due to heartbeat timeout")

    except Exception as e:
        logger.error(f"Error in heartbeat_checker: {e}", exc_info=True)


@shared_task
def force_offline_user(user_id, is_staff=False):
    try:
        if not redis_instance:
            return False

        user_id = str(user_id)
        online_set = "online_staff" if is_staff else "online_users"
        redis_instance.srem(online_set, user_id)
        cache.delete(f"user:{user_id}:connections")
        cache.delete(f"user:{user_id}:status")
        cache.delete(f"user:{user_id}:last_heartbeat")
        
        logger.info(f"Forced user {user_id} offline")
        return True

    except Exception as e:
        logger.error(f"Error forcing user offline: {e}", exc_info=True)
        return False
    

