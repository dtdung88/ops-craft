from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException
from typing import Dict, Set
import json
import asyncio
import logging
from app.core.security import decode_token

router = APIRouter()
logger = logging.getLogger(__name__)

# Store active WebSocket connections
class ConnectionManager:
    def __init__(self):
        # execution_id -> Set of WebSocket connections
        self.active_connections: Dict[int, Set[WebSocket]] = {}
        self._lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket, execution_id: int):
        """Accept and register a WebSocket connection"""
        try:
            await websocket.accept()
            async with self._lock:
                if execution_id not in self.active_connections:
                    self.active_connections[execution_id] = set()
                self.active_connections[execution_id].add(websocket)
                count = len(self.active_connections[execution_id])
                logger.info(f"WebSocket connected for execution {execution_id}. Total connections: {count}")
        except Exception as e:
            logger.error(f"Error accepting WebSocket connection: {e}")
            raise
    
    async def disconnect(self, websocket: WebSocket, execution_id: int):
        """Remove a WebSocket connection"""
        async with self._lock:
            if execution_id in self.active_connections:
                self.active_connections[execution_id].discard(websocket)
                remaining = len(self.active_connections[execution_id])
                logger.info(f"WebSocket disconnected for execution {execution_id}. Remaining: {remaining}")
                
                if not self.active_connections[execution_id]:
                    del self.active_connections[execution_id]
                    logger.info(f"All connections closed for execution {execution_id}")
    
    async def send_message(self, execution_id: int, message: dict):
        """Send message to all connections watching this execution"""
        if execution_id not in self.active_connections:
            return
        
        dead_connections = set()
        message_json = json.dumps(message)
        
        # Create a copy of connections to iterate safely
        connections = list(self.active_connections.get(execution_id, set()))
        
        for connection in connections:
            try:
                await connection.send_text(message_json)
            except (WebSocketDisconnect, RuntimeError) as e:
                logger.warning(f"Connection lost while sending message: {e}")
                dead_connections.add(connection)
            except Exception as e:
                logger.error(f"Error sending message to WebSocket: {e}")
                dead_connections.add(connection)
        
        # Clean up dead connections
        for connection in dead_connections:
            await self.disconnect(connection, execution_id)
    
    async def broadcast_log(self, execution_id: int, log_type: str, content: str):
        """Broadcast log message to all watchers"""
        message = {
            "type": "log",
            "log_type": log_type,  # "stdout", "stderr", "info", "error"
            "content": content,
            "execution_id": execution_id
        }
        await self.send_message(execution_id, message)
    
    async def broadcast_status(self, execution_id: int, status: str, metadata: dict = None):
        """Broadcast status update"""
        message = {
            "type": "status",
            "status": status,
            "execution_id": execution_id,
            "metadata": metadata or {}
        }
        await self.send_message(execution_id, message)
    
    def get_connection_count(self, execution_id: int = None) -> int:
        """Get total number of active connections"""
        if execution_id:
            return len(self.active_connections.get(execution_id, set()))
        return sum(len(conns) for conns in self.active_connections.values())


manager = ConnectionManager()


@router.websocket("/ws/executions/{execution_id}")
async def websocket_endpoint(
    websocket: WebSocket, 
    execution_id: int,
    token: str = Query(...)
):
    """
    WebSocket endpoint for real-time execution logs
    
    Requires JWT token in query parameter for authentication
    """
    # Verify authentication token
    try:
        payload = decode_token(token)
        if not payload:
            logger.warning(f"Invalid token for WebSocket connection to execution {execution_id}")
            await websocket.close(code=4001, reason="Invalid authentication token")
            return
        
        # Verify token type
        token_type = payload.get("type", "access")
        if token_type != "access":
            logger.warning(f"Wrong token type '{token_type}' for WebSocket connection")
            await websocket.close(code=4001, reason="Invalid token type")
            return
            
        username = payload.get("sub")
        user_id = payload.get("user_id")
        
        if not username or not user_id:
            logger.warning(f"Missing user info in token for execution {execution_id}")
            await websocket.close(code=4001, reason="Invalid token payload")
            return
            
        logger.info(f"WebSocket authentication successful for user {username} (execution {execution_id})")
        
    except Exception as e:
        logger.error(f"Token verification failed: {e}")
        await websocket.close(code=4001, reason="Authentication failed")
        return
    
    # Connect the WebSocket
    try:
        await manager.connect(websocket, execution_id)
    except Exception as e:
        logger.error(f"Failed to connect WebSocket: {e}")
        return
    
    try:
        # Send initial connection confirmation
        await websocket.send_json({
            "type": "connected",
            "execution_id": execution_id,
            "message": f"Connected to execution {execution_id} stream",
            "connection_count": manager.get_connection_count(execution_id)
        })
        
        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Set a timeout to prevent hanging connections
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=300.0  # 5 minutes timeout
                )
                
                # Handle client messages
                try:
                    message = json.loads(data)
                    message_type = message.get("type")
                    
                    if message_type == "ping":
                        await websocket.send_json({
                            "type": "pong",
                            "timestamp": asyncio.get_event_loop().time()
                        })
                        logger.debug(f"Pong sent to execution {execution_id}")
                    
                    elif message_type == "status_request":
                        # Client requesting current status
                        await websocket.send_json({
                            "type": "status_response",
                            "execution_id": execution_id,
                            "connected": True,
                            "connection_count": manager.get_connection_count(execution_id)
                        })
                    
                    else:
                        logger.debug(f"Unknown message type: {message_type}")
                    
                except json.JSONDecodeError:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Invalid JSON format"
                    })
                    
            except asyncio.TimeoutError:
                # Send keepalive ping
                try:
                    await websocket.send_json({
                        "type": "keepalive",
                        "message": "Connection active"
                    })
                    logger.debug(f"Keepalive sent to execution {execution_id}")
                except Exception:
                    logger.warning(f"Failed to send keepalive to execution {execution_id}")
                    break
                    
            except WebSocketDisconnect:
                logger.info(f"Client disconnected from execution {execution_id}")
                break
                
            except Exception as e:
                logger.error(f"Error in WebSocket loop for execution {execution_id}: {e}")
                try:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Server error: {str(e)}"
                    })
                except Exception:
                    pass
                break
    
    except Exception as e:
        logger.error(f"WebSocket error for execution {execution_id}: {e}")
    
    finally:
        await manager.disconnect(websocket, execution_id)


@router.get("/ws/stats")
async def websocket_stats():
    """Get WebSocket connection statistics"""
    return {
        "total_connections": manager.get_connection_count(),
        "active_executions": len(manager.active_connections),
        "connections_by_execution": {
            exec_id: len(conns) 
            for exec_id, conns in manager.active_connections.items()
        }
    }


# Helper functions to be used by Celery tasks
async def broadcast_execution_log(execution_id: int, log_type: str, content: str):
    """
    Function to be called from Celery tasks to broadcast logs
    """
    await manager.broadcast_log(execution_id, log_type, content)


async def broadcast_execution_status(execution_id: int, status: str, metadata: dict = None):
    """
    Function to be called from Celery tasks to broadcast status updates
    """
    await manager.broadcast_status(execution_id, status, metadata)

@router.post("/ws/test/{execution_id}")
async def test_websocket_broadcast(execution_id: int):
    """
    Test endpoint to manually send WebSocket messages
    
    Usage:
    curl -X POST http://localhost:8000/api/v1/ws/test/1 \
         -H "Authorization: Bearer YOUR_TOKEN"
    """
    import asyncio
    
    # Send test messages
    messages = [
        ("info", "🧪 Test message 1"),
        ("stdout", "🧪 Test message 2"),
        ("stdout", "🧪 Test message 3"),
        ("info", "✅ Test complete")
    ]
    
    for log_type, content in messages:
        await manager.broadcast_log(execution_id, log_type, content + "\n")
        await asyncio.sleep(1)  # 1 second delay between messages
    
    return {
        "success": True,
        "execution_id": execution_id,
        "messages_sent": len(messages),
        "active_connections": manager.get_connection_count(execution_id)
    }

@router.get("/ws/debug/{execution_id}")
async def debug_websocket_connections(execution_id: int):
    """
    Debug endpoint to check WebSocket connections
    
    Usage:
    curl http://localhost:8000/api/v1/ws/debug/1
    """
    return {
        "execution_id": execution_id,
        "active_connections": manager.get_connection_count(execution_id),
        "connection_exists": execution_id in manager.active_connections,
        "total_connections": manager.get_connection_count(),
        "all_executions": list(manager.active_connections.keys())
    }