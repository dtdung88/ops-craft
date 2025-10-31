"""
Redis Pub/Sub bridge - VERIFIED WORKING VERSION
File: backend/app/core/websocket_bridge.py
"""
import redis
import json
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)


class WebSocketBridge:
    """Bridge between Celery and WebSocket using Redis Pub/Sub"""
    
    def __init__(self):
        try:
            self.redis_client = redis.from_url(
                settings.REDIS_URL, 
                decode_responses=True,
                socket_connect_timeout=5
            )
            # Test connection
            self.redis_client.ping()
            logger.info("[REDIS-BRIDGE] Connected to Redis successfully")
        except Exception as e:
            logger.error(f"[REDIS-BRIDGE] Failed to connect to Redis: {e}")
            raise
    
    def publish_log(self, execution_id: int, log_type: str, content: str):
        """Publish log message to Redis (called from Celery worker)"""
        try:
            channel = f"execution:{execution_id}"
            message = {
                "type": "log",
                "log_type": log_type,
                "content": content,
                "execution_id": execution_id
            }
            result = self.redis_client.publish(channel, json.dumps(message))
            logger.info(f"[REDIS-BRIDGE] Published log to {channel}, subscribers: {result}")
            return result
        except Exception as e:
            logger.error(f"[REDIS-BRIDGE] Failed to publish log: {e}")
            return 0
    
    def publish_status(self, execution_id: int, status: str, metadata: dict = None):
        """Publish status update to Redis (called from Celery worker)"""
        try:
            channel = f"execution:{execution_id}"
            message = {
                "type": "status",
                "status": status,
                "execution_id": execution_id,
                "metadata": metadata or {}
            }
            result = self.redis_client.publish(channel, json.dumps(message))
            logger.info(f"[REDIS-BRIDGE] Published status to {channel}, subscribers: {result}")
            return result
        except Exception as e:
            logger.error(f"[REDIS-BRIDGE] Failed to publish status: {e}")
            return 0
    
    def subscribe(self, execution_id: int):
        """Subscribe to Redis channel (called from WebSocket)"""
        try:
            channel = f"execution:{execution_id}"
            pubsub = self.redis_client.pubsub()
            pubsub.subscribe(channel)
            logger.info(f"[REDIS-BRIDGE] Subscribed to {channel}")
            return pubsub
        except Exception as e:
            logger.error(f"[REDIS-BRIDGE] Failed to subscribe: {e}")
            return None
    
    def close(self):
        """Close Redis connection"""
        try:
            self.redis_client.close()
        except Exception as e:
            logger.error(f"[REDIS-BRIDGE] Error closing connection: {e}")


# Global instance for use across the app
websocket_bridge = WebSocketBridge()