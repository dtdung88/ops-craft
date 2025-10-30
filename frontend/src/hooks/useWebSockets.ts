import { useEffect, useRef, useState, useCallback } from 'react';

export interface WebSocketMessage {
    type: 'connected' | 'log' | 'status' | 'error' | 'pong' | 'keepalive';
    execution_id?: number;
    log_type?: 'stdout' | 'stderr' | 'info' | 'error';
    content?: string;
    status?: string;
    metadata?: any;
    message?: string;
    connection_count?: number;
    timestamp?: number;
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
        reconnectAttempts = 3,
    } = options;

    const [isConnected, setIsConnected] = useState(false);
    const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
    const wsRef = useRef<WebSocket | null>(null);
    const reconnectCountRef = useRef(0);
    const reconnectTimeoutRef = useRef<NodeJS.Timeout>();
    const pingIntervalRef = useRef<NodeJS.Timeout>();
    const shouldReconnectRef = useRef(true);
    const mountedRef = useRef(true);
    const isConnectingRef = useRef(false);
    const urlRef = useRef<string | null>(null);

    const cleanup = useCallback(() => {
        console.log('[WebSocket] Cleaning up...');

        // Clear timers
        if (reconnectTimeoutRef.current) {
            clearTimeout(reconnectTimeoutRef.current);
            reconnectTimeoutRef.current = undefined;
        }

        if (pingIntervalRef.current) {
            clearInterval(pingIntervalRef.current);
            pingIntervalRef.current = undefined;
        }

        // Close WebSocket connection
        if (wsRef.current) {
            const ws = wsRef.current;
            wsRef.current = null;

            // Remove all event listeners
            ws.onopen = null;
            ws.onclose = null;
            ws.onerror = null;
            ws.onmessage = null;

            try {
                if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
                    ws.close(1000, 'Component cleanup');
                }
            } catch (error) {
                console.warn('[WebSocket] Error during cleanup:', error);
            }
        }

        isConnectingRef.current = false;
        setIsConnected(false);
    }, []);

    const connect = useCallback(() => {
        // Don't connect if URL hasn't changed and already connecting/connected
        if (!url || !mountedRef.current || isConnectingRef.current) {
            return;
        }

        // Only cleanup if URL changed
        if (wsRef.current && urlRef.current !== url) {
            cleanup();
        }

        // Don't reconnect if already connected to same URL
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN && urlRef.current === url) {
            console.log('[WebSocket] Already connected to', url);
            return;
        }

        // Validate URL
        if (!url || url === '') {
            console.warn('[WebSocket] Invalid URL provided');
            return;
        }

        isConnectingRef.current = true;
        urlRef.current = url;
        console.log('[WebSocket] Connecting to:', url);

        try {
            const ws = new WebSocket(url);
            wsRef.current = ws;

            ws.onopen = () => {
                if (!mountedRef.current) {
                    ws.close();
                    return;
                }

                console.log('[WebSocket] Connected successfully');
                setIsConnected(true);
                reconnectCountRef.current = 0;
                isConnectingRef.current = false;
                onOpen?.();

                // Start ping interval
                pingIntervalRef.current = setInterval(() => {
                    if (ws.readyState === WebSocket.OPEN) {
                        try {
                            ws.send(JSON.stringify({ type: 'ping' }));
                            console.log('[WebSocket] Ping sent');
                        } catch (error) {
                            console.error('[WebSocket] Error sending ping:', error);
                        }
                    } else {
                        if (pingIntervalRef.current) {
                            clearInterval(pingIntervalRef.current);
                        }
                    }
                }, 30000);
            };

            ws.onmessage = (event) => {
                if (!mountedRef.current) return;

                try {
                    const message: WebSocketMessage = JSON.parse(event.data);
                    console.log('[WebSocket] Message received:', message.type);
                    setLastMessage(message);
                    onMessage?.(message);
                } catch (error) {
                    console.error('[WebSocket] Failed to parse message:', error);
                }
            };

            ws.onerror = (event) => {
                console.error('[WebSocket] Error occurred:', event);
                isConnectingRef.current = false;
                onError?.(event);
            };

            ws.onclose = (event) => {
                console.log(`[WebSocket] Disconnected (Code: ${event.code}, Reason: ${event.reason || 'None'})`);

                // Clear ping interval
                if (pingIntervalRef.current) {
                    clearInterval(pingIntervalRef.current);
                    pingIntervalRef.current = undefined;
                }

                setIsConnected(false);
                isConnectingRef.current = false;
                wsRef.current = null;
                onClose?.();

                // Attempt reconnection if appropriate
                if (
                    mountedRef.current &&
                    shouldReconnectRef.current &&
                    event.code !== 1000 &&
                    reconnectCountRef.current < reconnectAttempts &&
                    reconnect &&
                    urlRef.current === url  // Only reconnect to same URL
                ) {
                    reconnectCountRef.current++;
                    console.log(
                        `[WebSocket] Reconnecting... Attempt ${reconnectCountRef.current}/${reconnectAttempts}`
                    );

                    reconnectTimeoutRef.current = setTimeout(() => {
                        if (mountedRef.current && shouldReconnectRef.current && urlRef.current === url) {
                            connect();
                        }
                    }, reconnectInterval);
                } else if (reconnectCountRef.current >= reconnectAttempts) {
                    console.log('[WebSocket] Max reconnection attempts reached');
                }
            };
        } catch (error) {
            console.error('[WebSocket] Failed to create WebSocket:', error);
            isConnectingRef.current = false;
        }
    }, [url, onOpen, onMessage, onClose, onError, reconnect, reconnectInterval, reconnectAttempts, cleanup]);

    const disconnect = useCallback(() => {
        console.log('[WebSocket] Manual disconnect requested');
        shouldReconnectRef.current = false;
        reconnectCountRef.current = reconnectAttempts;
        cleanup();
    }, [cleanup, reconnectAttempts]);

    const sendMessage = useCallback((message: any) => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
            try {
                wsRef.current.send(JSON.stringify(message));
                console.log('[WebSocket] Message sent:', message.type || 'message');
                return true;
            } catch (error) {
                console.error('[WebSocket] Failed to send message:', error);
                return false;
            }
        }
        console.warn('[WebSocket] Cannot send message - not connected');
        return false;
    }, []);

    // Connection effect - ONLY runs when URL changes
    useEffect(() => {
        mountedRef.current = true;
        shouldReconnectRef.current = true;

        if (url && url !== '' && url !== urlRef.current) {
            const connectTimeout = setTimeout(() => {
                if (mountedRef.current) {
                    connect();
                }
            }, 100);

            return () => {
                clearTimeout(connectTimeout);
            };
        }

        return undefined;
    }, [url, connect]);

    // Cleanup on unmount ONLY
    useEffect(() => {
        return () => {
            console.log('[WebSocket] Component unmounting');
            mountedRef.current = false;
            shouldReconnectRef.current = false;
            cleanup();
        };
    }, [cleanup]);

    return {
        isConnected,
        lastMessage,
        sendMessage,
        disconnect,
        reconnect: connect,
    };
};