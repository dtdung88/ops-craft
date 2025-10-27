from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from typing import Dict, Set
import json
import asyncio
from app.api.dependencies import get_current_user
from app.models.user import User

router = APIRouter()

# Store active WebSocket connections
class ConnectionManager:
    def __init__(self):
        # execution_id -> Set of WebSocket connections
        self.active_connections: Dict[int, Set[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, execution_id: int):
        """Accept and register a WebSocket connection"""
        await websocket.accept()
        if execution_id not in self.active_connections:
            self.active_connections[execution_id] = set()
        self.active_connections[execution_id].add(websocket)
    
    def disconnect(self, websocket: WebSocket, execution_id: int):
        """Remove a WebSocket connection"""
        if execution_id in self.active_connections:
            self.active_connections[execution_id].discard(websocket)
            if not self.active_connections[execution_id]:
                del self.active_connections[execution_id]
    
    async def send_message(self, execution_id: int, message: dict):
        """Send message to all connections watching this execution"""
        if execution_id not in self.active_connections:
            return
        
        dead_connections = set()
        for connection in self.active_connections[execution_id]:
            try:
                await connection.send_json(message)
            except Exception:
                dead_connections.add(connection)
        
        # Clean up dead connections
        for connection in dead_connections:
            self.disconnect(connection, execution_id)
    
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


manager = ConnectionManager()


@router.websocket("/ws/executions/{execution_id}")
async def websocket_endpoint(websocket: WebSocket, execution_id: int):
    """
    WebSocket endpoint for real-time execution logs
    
    Client should send JWT token in query params or first message for auth
    """
    await manager.connect(websocket, execution_id)
    
    try:
        # Send initial connection confirmation
        await websocket.send_json({
            "type": "connected",
            "execution_id": execution_id,
            "message": "Connected to execution stream"
        })
        
        # Keep connection alive and handle incoming messages
        while True:
            try:
                data = await websocket.receive_text()
                # Handle client messages if needed (like pause, cancel, etc.)
                message = json.loads(data)
                
                if message.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
                    
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON"
                })
            except Exception as e:
                await websocket.send_json({
                    "type": "error",
                    "message": str(e)
                })
                break
    
    finally:
        manager.disconnect(websocket, execution_id)


# Helper function to be used by Celery tasks
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