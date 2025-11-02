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

    // FIX: Store URL in ref to prevent reconnections on re-render
    const urlRef = useRef<string | null>(null);

    const cleanup = useCallback(() => {
        if (reconnectTimeoutRef.current) {
            clearTimeout(reconnectTimeoutRef.current);
        }
        if (heartbeatTimeoutRef.current) {
            clearTimeout(heartbeatTimeoutRef.current);
        }
        if (wsRef.current) {
            // Remove event listeners before closing
            wsRef.current.onopen = null;
            wsRef.current.onmessage = null;
            wsRef.current.onerror = null;
            wsRef.current.onclose = null;

            if (wsRef.current.readyState === WebSocket.OPEN ||
                wsRef.current.readyState === WebSocket.CONNECTING) {
                wsRef.current.close(1000, 'Component unmounting');
            }
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
                try {
                    wsRef.current.send(JSON.stringify({ type: 'ping' }));
                    startHeartbeat();
                } catch (error) {
                    console.error('[WS] Heartbeat send failed:', error);
                }
            }
        }, heartbeatInterval);
    }, [heartbeatInterval]);

    const connect = useCallback(() => {
        // FIX: Don't reconnect if URL hasn't changed and connection exists
        if (!url || !mountedRef.current) return;

        // Prevent duplicate connections
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
            console.log('[WS] Already connected, skipping');
            return;
        }

        if (wsRef.current && wsRef.current.readyState === WebSocket.CONNECTING) {
            console.log('[WS] Connection in progress, skipping');
            return;
        }

        cleanup();

        try {
            console.log('[WS] Connecting to:', url);
            const ws = new WebSocket(url);
            wsRef.current = ws;

            ws.onopen = () => {
                if (!mountedRef.current) {
                    ws.close();
                    return;
                }

                console.log('[WS] Connected successfully');
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
                    startHeartbeat(); // Reset heartbeat on message
                } catch (error) {
                    console.error('[WS] Failed to parse message:', error);
                }
            };

            ws.onerror = (event) => {
                console.error('[WS] Error:', event);
                onError?.(event);
            };

            ws.onclose = (event) => {
                console.log('[WS] Closed:', event.code, event.reason);
                setIsConnected(false);
                wsRef.current = null;
                onClose?.();

                if (heartbeatTimeoutRef.current) {
                    clearTimeout(heartbeatTimeoutRef.current);
                }

                // Only reconnect if intentional disconnect
                if (
                    mountedRef.current &&
                    shouldReconnectRef.current &&
                    reconnectCountRef.current < reconnectAttempts &&
                    reconnect &&
                    event.code !== 1000 // Normal closure
                ) {
                    reconnectCountRef.current++;
                    console.log(
                        `[WS] Reconnecting... Attempt ${reconnectCountRef.current}/${reconnectAttempts}`
                    );

                    reconnectTimeoutRef.current = setTimeout(() => {
                        if (mountedRef.current && shouldReconnectRef.current) {
                            connect();
                        }
                    }, reconnectInterval);
                }
            };
        } catch (error) {
            console.error('[WS] Failed to create WebSocket:', error);
        }
    }, [url, onOpen, onMessage, onClose, onError, reconnect, reconnectInterval,
        reconnectAttempts, cleanup, startHeartbeat]);

    const disconnect = useCallback(() => {
        console.log('[WS] Manual disconnect requested');
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
                console.error('[WS] Failed to send message:', error);
                return false;
            }
        }
        console.warn('[WS] Cannot send message, not connected');
        return false;
    }, []);

    // FIX: Only connect when URL actually changes
    useEffect(() => {
        mountedRef.current = true;
        shouldReconnectRef.current = true;

        // Only connect if URL changed
        if (url && url !== urlRef.current) {
            console.log('[WS] URL changed, connecting...');
            urlRef.current = url;
            connect();
        } else if (!url && urlRef.current) {
            console.log('[WS] URL removed, disconnecting...');
            urlRef.current = null;
            cleanup();
        }

        return () => {
            console.log('[WS] Component unmounting, cleanup');
            mountedRef.current = false;
            shouldReconnectRef.current = false;
            urlRef.current = null;
            cleanup();
        };
    }, [url]); // Only depend on url

    return {
        isConnected,
        lastMessage,
        sendMessage,
        disconnect,
        reconnect: connect
    };
};