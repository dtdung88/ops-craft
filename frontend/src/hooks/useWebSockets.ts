import { useEffect, useRef, useState, useCallback } from 'react';

export interface WebSocketMessage {
    type: 'connected' | 'log' | 'status' | 'error' | 'pong';
    execution_id?: number;
    log_type?: 'stdout' | 'stderr' | 'info' | 'error';
    content?: string;
    status?: string;
    metadata?: any;
    message?: string;
}

interface UseWebSocketOptions {
    onMessage?: (message: WebSocketMessage) => void;
    onOpen?: () => void;
    onClose?: () => void;
    onError?: (error: Event) => void;
    reconnect?: boolean;
    reconnectInterval?: number;
    reconnectAttempts?: number;
}

export const useWebSocket = (
    url: string | null,
    options: UseWebSocketOptions = {}
) => {
    const {
        onMessage,
        onOpen,
        onClose,
        onError,
        reconnect = true,
        reconnectInterval = 3000,
        reconnectAttempts = 5,
    } = options;

    const [isConnected, setIsConnected] = useState(false);
    const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
    const wsRef = useRef<WebSocket | null>(null);
    const reconnectCountRef = useRef(0);
    const reconnectTimeoutRef = useRef<NodeJS.Timeout>();
    const shouldReconnectRef = useRef(true);
    const mountedRef = useRef(true);

    const connect = useCallback(() => {
        if (!url || !mountedRef.current) return;

        // Clear any existing connection
        if (wsRef.current) {
            wsRef.current.close();
            wsRef.current = null;
        }

        try {
            console.log(`[WebSocket] Connecting to: ${url}`);
            const ws = new WebSocket(url);

            ws.onopen = () => {
                if (!mountedRef.current) {
                    ws.close();
                    return;
                }

                console.log('[WebSocket] Connected successfully');
                setIsConnected(true);
                reconnectCountRef.current = 0;
                onOpen?.();
            };

            ws.onmessage = (event) => {
                if (!mountedRef.current) return;

                try {
                    const message: WebSocketMessage = JSON.parse(event.data);
                    console.log('[WebSocket] Received:', message.type);
                    setLastMessage(message);
                    onMessage?.(message);
                } catch (error) {
                    console.error('[WebSocket] Failed to parse message:', error);
                }
            };

            ws.onclose = (event) => {
                if (!mountedRef.current) return;

                console.log(`[WebSocket] Disconnected (Code: ${event.code})`);
                setIsConnected(false);
                wsRef.current = null;
                onClose?.();

                // Attempt reconnection if enabled and haven't exceeded attempts
                if (
                    shouldReconnectRef.current &&
                    reconnect &&
                    reconnectCountRef.current < reconnectAttempts
                ) {
                    reconnectCountRef.current += 1;
                    console.log(
                        `[WebSocket] Reconnecting... Attempt ${reconnectCountRef.current}/${reconnectAttempts}`
                    );

                    reconnectTimeoutRef.current = setTimeout(() => {
                        if (mountedRef.current) {
                            connect();
                        }
                    }, reconnectInterval);
                } else if (reconnectCountRef.current >= reconnectAttempts) {
                    console.log('[WebSocket] Max reconnection attempts reached');
                }
            };

            ws.onerror = (error) => {
                console.error('[WebSocket] Error:', error);
                onError?.(error);
            };

            wsRef.current = ws;
        } catch (error) {
            console.error('[WebSocket] Failed to create connection:', error);
        }
    }, [url, onMessage, onOpen, onClose, onError, reconnect, reconnectInterval, reconnectAttempts]);

    const disconnect = useCallback(() => {
        console.log('[WebSocket] Disconnecting...');
        shouldReconnectRef.current = false;

        if (reconnectTimeoutRef.current) {
            clearTimeout(reconnectTimeoutRef.current);
            reconnectTimeoutRef.current = undefined;
        }

        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
            wsRef.current.close();
        }

        wsRef.current = null;
        setIsConnected(false);
    }, []);

    const sendMessage = useCallback((message: any) => {
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
            try {
                wsRef.current.send(JSON.stringify(message));
                console.log('[WebSocket] Sent:', message.type || 'message');
            } catch (error) {
                console.error('[WebSocket] Failed to send message:', error);
            }
        } else {
            console.warn('[WebSocket] Cannot send message - not connected');
        }
    }, []);

    const ping = useCallback(() => {
        sendMessage({ type: 'ping' });
    }, [sendMessage]);

    // Initial connection
    useEffect(() => {
        mountedRef.current = true;
        shouldReconnectRef.current = true;

        if (url) {
            connect();
        }

        return () => {
            mountedRef.current = false;
            shouldReconnectRef.current = false;
            disconnect();
        };
    }, [url, connect, disconnect]);

    // Ping interval to keep connection alive
    useEffect(() => {
        if (!isConnected) return;

        const interval = setInterval(() => {
            if (mountedRef.current && isConnected) {
                ping();
            }
        }, 30000); // Ping every 30 seconds

        return () => clearInterval(interval);
    }, [isConnected, ping]);

    return {
        isConnected,
        lastMessage,
        sendMessage,
        disconnect,
        reconnect: connect,
    };
};