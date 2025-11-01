import { useEffect, useRef, useState, useCallback } from 'react';

export interface WebSocketMessage {
    type: 'connected' | 'log' | 'status' | 'error' | 'pong' | 'keepalive';
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
    heartbeatInterval?: number;
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
        heartbeatInterval = 30000
    } = options;

    const [isConnected, setIsConnected] = useState(false);
    const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
    const wsRef = useRef<WebSocket | null>(null);
    const reconnectCountRef = useRef(0);
    const reconnectTimeoutRef = useRef<NodeJS.Timeout>();
    const heartbeatTimeoutRef = useRef<NodeJS.Timeout>();
    const shouldReconnectRef = useRef(true);
    const mountedRef = useRef(true);

    const cleanup = useCallback(() => {
        if (reconnectTimeoutRef.current) {
            clearTimeout(reconnectTimeoutRef.current);
        }
        if (heartbeatTimeoutRef.current) {
            clearTimeout(heartbeatTimeoutRef.current);
        }
        if (wsRef.current) {
            wsRef.current.close();
            wsRef.current = null;
        }
        setIsConnected(false);
    }, []);

    const startHeartbeat = useCallback(() => {
        if (heartbeatTimeoutRef.current) {
            clearTimeout(heartbeatTimeoutRef.current);
        }

        heartbeatTimeoutRef.current = setTimeout(() => {
            if (wsRef.current?.readyState === WebSocket.OPEN) {
                wsRef.current.send(JSON.stringify({ type: 'ping' }));
                startHeartbeat();
            }
        }, heartbeatInterval);
    }, [heartbeatInterval]);

    const connect = useCallback(() => {
        if (!url || !mountedRef.current) return;

        cleanup();

        try {
            const ws = new WebSocket(url);
            wsRef.current = ws;

            ws.onopen = () => {
                if (!mountedRef.current) {
                    ws.close();
                    return;
                }

                setIsConnected(true);
                reconnectCountRef.current = 0;
                onOpen?.();
                startHeartbeat();
            };

            ws.onmessage = (event) => {
                if (!mountedRef.current) return;

                try {
                    const message: WebSocketMessage = JSON.parse(event.data);
                    setLastMessage(message);
                    onMessage?.(message);

                    // Reset heartbeat on message
                    startHeartbeat();
                } catch (error) {
                    console.error('Failed to parse WebSocket message:', error);
                }
            };

            ws.onerror = (event) => {
                console.error('WebSocket error:', event);
                onError?.(event);
            };

            ws.onclose = (event) => {
                setIsConnected(false);
                wsRef.current = null;
                onClose?.();

                if (heartbeatTimeoutRef.current) {
                    clearTimeout(heartbeatTimeoutRef.current);
                }

                if (
                    mountedRef.current &&
                    shouldReconnectRef.current &&
                    reconnectCountRef.current < reconnectAttempts &&
                    reconnect &&
                    event.code !== 1000
                ) {
                    reconnectCountRef.current++;
                    console.log(
                        `Reconnecting... Attempt ${reconnectCountRef.current}/${reconnectAttempts}`
                    );

                    reconnectTimeoutRef.current = setTimeout(() => {
                        if (mountedRef.current && shouldReconnectRef.current) {
                            connect();
                        }
                    }, reconnectInterval);
                }
            };
        } catch (error) {
            console.error('Failed to create WebSocket:', error);
        }
    }, [url, onOpen, onMessage, onClose, onError, reconnect, reconnectInterval,
        reconnectAttempts, cleanup, startHeartbeat]);

    const disconnect = useCallback(() => {
        shouldReconnectRef.current = false;
        reconnectCountRef.current = reconnectAttempts;
        cleanup();
    }, [cleanup, reconnectAttempts]);

    const sendMessage = useCallback((message: any) => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
            try {
                wsRef.current.send(JSON.stringify(message));
                return true;
            } catch (error) {
                console.error('Failed to send WebSocket message:', error);
                return false;
            }
        }
        return false;
    }, []);

    useEffect(() => {
        mountedRef.current = true;
        shouldReconnectRef.current = true;

        if (url) {
            connect();
        }

        return () => {
            mountedRef.current = false;
            shouldReconnectRef.current = false;
            cleanup();
        };
    }, [url, connect, cleanup]);

    return {
        isConnected,
        lastMessage,
        sendMessage,
        disconnect,
        reconnect: connect
    };
};