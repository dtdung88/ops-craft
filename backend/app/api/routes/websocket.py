"""
WebSocket endpoint with Redis Pub/Sub listener - FIXED EVENT LOOP VERSION
File: backend/app/api/routes/websocket.py
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import Dict, Set, Optional
import json
import asyncio
import logging
import threading
from app.core.security import decode_token
from app.core.websocket_bridge import WebSocketBridge

router = APIRouter()
logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections and Redis listeners"""
    
    def __init__(self):
        self.active_connections: Dict[int, Set[WebSocket]] = {}
        self._lock = asyncio.Lock()
        self.redis_tasks: Dict[int, threading.Thread] = {}
        self.stop_signals: Dict[int, threading.Event] = {}
        self.main_loop: Optional[asyncio.AbstractEventLoop] = None
    
    async def connect(self, websocket: WebSocket, execution_id: int):
        """Connect WebSocket and start Redis listener"""
        await websocket.accept()
        
        # Store reference to main event loop on first connection
        if self.main_loop is None:
            self.main_loop = asyncio.get_running_loop()
            logger.info("[WS] Stored reference to main event loop")
        
        async with self._lock:
            if execution_id not in self.active_connections:
                self.active_connections[execution_id] = set()
            
            self.active_connections[execution_id].add(websocket)
            logger.info(f"[WS] Connected for execution {execution_id}, total: {len(self.active_connections[execution_id])}")
            
            # Start Redis listener if not running
            if execution_id not in self.redis_tasks:
                stop_signal = threading.Event()
                self.stop_signals[execution_id] = stop_signal
                
                thread = threading.Thread(
                    target=self._redis_listener_thread,
                    args=(execution_id, stop_signal),
                    daemon=True
                )
                self.redis_tasks[execution_id] = thread
                thread.start()
                logger.info(f"[WS] Started Redis listener for execution {execution_id}")
    
    async def disconnect(self, websocket: WebSocket, execution_id: int):
        """Disconnect WebSocket"""
        async with self._lock:
            if execution_id in self.active_connections:
                self.active_connections[execution_id].discard(websocket)
                remaining = len(self.active_connections[execution_id])
                logger.info(f"[WS] Disconnected from execution {execution_id}, remaining: {remaining}")
                
                # Stop Redis listener if no more connections
                if not self.active_connections[execution_id]:
                    del self.active_connections[execution_id]
                    
                    if execution_id in self.stop_signals:
                        self.stop_signals[execution_id].set()
                        del self.stop_signals[execution_id]
                    
                    if execution_id in self.redis_tasks:
                        del self.redis_tasks[execution_id]
                    
                    logger.info(f"[WS] Stopped Redis listener for execution {execution_id}")
    
    def _redis_listener_thread(self, execution_id: int, stop_signal: threading.Event):
        """Thread that listens to Redis and forwards to WebSockets"""
        logger.info(f"[REDIS-LISTENER] Started for execution {execution_id}")
        
        bridge = WebSocketBridge()
        pubsub = bridge.subscribe(execution_id)
        
        if not pubsub:
            logger.error(f"[REDIS-LISTENER] Failed to subscribe for execution {execution_id}")
            return
        
        try:
            # Listen for messages
            for message in pubsub.listen():
                # Check stop signal
                if stop_signal.is_set():
                    logger.info(f"[REDIS-LISTENER] Stop signal received for execution {execution_id}")
                    break
                
                # Process message
                if message['type'] == 'message':
                    try:
                        data = json.loads(message['data'])
                        logger.info(f"[REDIS-LISTENER] Received {data.get('type')} for execution {execution_id}")
                        
                        # Send to all WebSocket connections
                        self._send_to_websockets(execution_id, data)
                        
                    except Exception as e:
                        logger.error(f"[REDIS-LISTENER] Error processing message: {e}")
            
        except Exception as e:
            logger.error(f"[REDIS-LISTENER] Error: {e}")
        finally:
            pubsub.close()
            bridge.close()
            logger.info(f"[REDIS-LISTENER] Stopped for execution {execution_id}")
    
    def _send_to_websockets(self, execution_id: int, message: dict):
        """Send message to all WebSocket connections (called from Redis thread)"""
        if execution_id not in self.active_connections:
            logger.warning(f"[WS] No active connections for execution {execution_id}")
            return
        
        if self.main_loop is None:
            logger.error("[WS] Main event loop not available!")
            return
        
        # Schedule the async send in the main event loop
        try:
            future = asyncio.run_coroutine_threadsafe(
                self._async_send(execution_id, message),
                self.main_loop
            )
            # Wait for it to complete (with timeout)
            future.result(timeout=1.0)
            logger.debug(f"[WS] Successfully sent message to execution {execution_id}")
        except Exception as e:
            logger.error(f"[WS] Failed to send message: {e}")
    
    async def _async_send(self, execution_id: int, message: dict):
        """Actually send to WebSockets (runs in main event loop)"""
        if execution_id not in self.active_connections:
            return
        
        message_json = json.dumps(message)
        dead_connections = set()
        
        connections = list(self.active_connections.get(execution_id, set()))
        logger.info(f"[WS] Sending to {len(connections)} connection(s) for execution {execution_id}")
        
        for websocket in connections:
            try:
                await websocket.send_text(message_json)
                logger.info(f"[WS] ✓ Sent {message.get('type')} to websocket")
            except Exception as e:
                logger.warning(f"[WS] Failed to send to websocket: {e}")
                dead_connections.add(websocket)
        
        # Clean up dead connections
        if dead_connections:
            async with self._lock:
                for ws in dead_connections:
                    if execution_id in self.active_connections:
                        self.active_connections[execution_id].discard(ws)


manager = ConnectionManager()


@router.websocket("/ws/executions/{execution_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    execution_id: int,
    token: str = Query(...)
):
    """WebSocket endpoint for real-time execution logs"""
    
    # Verify token
    try:
        payload = decode_token(token)
        if not payload or payload.get("type") != "access":
            await websocket.close(code=4001, reason="Invalid token")
            return
        
        username = payload.get("sub")
        if not username:
            await websocket.close(code=4001, reason="Invalid token")
            return
        
        logger.info(f"[WS] Auth successful for {username}, execution {execution_id}")
        
    except Exception as e:
        logger.error(f"[WS] Auth failed: {e}")
        await websocket.close(code=4001, reason="Auth failed")
        return
    
    # Connect
    try:
        await manager.connect(websocket, execution_id)
    except Exception as e:
        logger.error(f"[WS] Connect failed: {e}")
        return
    
    try:
        # Send connection confirmation
        await websocket.send_json({
            "type": "connected",
            "execution_id": execution_id,
            "message": f"Connected to execution {execution_id}"
        })
        
        # Keep connection alive
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=300.0)
                
                # Handle client messages
                try:
                    msg = json.loads(data)
                    if msg.get("type") == "ping":
                        await websocket.send_json({"type": "pong"})
                except:
                    pass
                    
            except asyncio.TimeoutError:
                # Send keepalive
                try:
                    await websocket.send_json({"type": "keepalive"})
                except:
                    break
                    
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"[WS] Loop error: {e}")
                break
    
    finally:
        await manager.disconnect(websocket, execution_id)


@router.get("/ws/stats")
async def websocket_stats():
    """Get WebSocket stats"""
    return {
        "total_connections": sum(len(conns) for conns in manager.active_connections.values()),
        "active_executions": len(manager.active_connections)
    }