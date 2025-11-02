import React, { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import { executionApi, getWebSocketUrl, Execution } from '../services/api';
import { useWebSocket, WebSocketMessage } from '../hooks/useWebSockets';
import { useAuth } from '../contexts/AuthContext';
import '../styles/ExecutionList.css';

const ExecutionList: React.FC = () => {
    const { user } = useAuth();
    const [selectedExecution, setSelectedExecution] = useState<Execution | null>(null);
    const [liveLog, setLiveLog] = useState<string>('');
    const [autoScroll, setAutoScroll] = useState(true);
    const [showToast, setShowToast] = useState<{ message: string; type: 'success' | 'error' | 'info' } | null>(null);
    const logContainerRef = useRef<HTMLDivElement>(null);

    const { data: executions, isLoading, error, refetch } = useQuery({
        queryKey: ['executions'],
        queryFn: async () => {
            const response = await executionApi.getAll();
            return response.data;
        },
        refetchInterval: 5000,
    });

    const wsUrl = useMemo(() => {
        if (!selectedExecution?.id) return null;
        const url = getWebSocketUrl(selectedExecution.id);
        console.log('[ExecutionList] Creating WebSocket URL:', url);
        return url;
    }, [selectedExecution?.id]);

    const handleWebSocketMessage = useCallback((message: WebSocketMessage) => {
        console.log('[ExecutionList] WebSocket message:', message.type);

        if (message.type === 'log' && message.content) {
            setLiveLog((prev) => prev + message.content);
        } else if (message.type === 'status' && message.status) {
            if (selectedExecution?.id) {
                fetchExecutionDetails(selectedExecution.id);
            }
            refetch();
        }
    }, [selectedExecution?.id, refetch]);

    const { isConnected } = useWebSocket(wsUrl, {
        onMessage: handleWebSocketMessage,
        onOpen: () => console.log('[ExecutionList] WebSocket connected'),
        onClose: () => console.log('[ExecutionList] WebSocket disconnected'),
        onError: (error) => console.error('[ExecutionList] WebSocket error:', error),
        reconnect: true,
        reconnectInterval: 3000,
        reconnectAttempts: 5,
    });

    const fetchExecutionDetails = async (executionId: number) => {
        try {
            const response = await executionApi.getById(executionId);
            setSelectedExecution(response.data);

            if (response.data.status !== 'running') {
                setLiveLog(response.data.output || '');
            }
        } catch (err) {
            console.error('Failed to fetch execution details:', err);
        }
    };

    useEffect(() => {
        if (!selectedExecution ||
            (selectedExecution.status !== 'running' &&
                selectedExecution.status !== 'pending')) {
            return;
        }

        const interval = setInterval(() => {
            fetchExecutionDetails(selectedExecution.id);
        }, 2000);

        return () => clearInterval(interval);
    }, [selectedExecution?.id, selectedExecution?.status]);

    useEffect(() => {
        if (autoScroll && logContainerRef.current) {
            logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
        }
    }, [liveLog, autoScroll]);

    const showNotification = (message: string, type: 'success' | 'error' | 'info') => {
        setShowToast({ message, type });
        setTimeout(() => setShowToast(null), 3000);
    };

    const handleViewDetails = useCallback(async (execution: Execution) => {
        console.log('[ExecutionList] Viewing execution:', execution.id);
        setSelectedExecution(execution);
        setLiveLog(execution.output || '');
        await fetchExecutionDetails(execution.id);
    }, []);

    const handleCloseModal = useCallback(() => {
        console.log('[ExecutionList] Closing modal');
        setSelectedExecution(null);
        setLiveLog('');
    }, []);

    const handleCancelExecution = async (id: number) => {
        try {
            await executionApi.cancel(id);
            showNotification('Execution cancelled successfully', 'success');
            refetch();
        } catch (error) {
            console.error('Failed to cancel execution:', error);
            showNotification('Failed to cancel execution', 'error');
        }
    };

    if (isLoading) return <div className="loading">Loading executions...</div>;
    if (error) return <div className="error">Error loading executions: {(error as Error).message}</div>;

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'success': return '#27ae60';
            case 'failed': return '#e74c3c';
            case 'running': return '#3498db';
            case 'pending': return '#f39c12';
            case 'cancelled': return '#95a5a6';
            default: return '#7f8c8d';
        }
    };

    const getStatusIcon = (status: string) => {
        switch (status) {
            case 'success': return '✓';
            case 'failed': return '✗';
            case 'running': return '⟳';
            case 'pending': return '⏱';
            case 'cancelled': return '⊘';
            default: return '?';
        }
    };

    const formatDate = (dateString: string) => {
        if (!dateString) return '-';
        return new Date(dateString).toLocaleString();
    };

    const calculateDuration = (execution: Execution) => {
        if (!execution.started_at) return '-';

        const start = new Date(execution.started_at).getTime();
        const end = execution.completed_at
            ? new Date(execution.completed_at).getTime()
            : Date.now();
        const duration = Math.round((end - start) / 1000);

        if (duration < 60) return `${duration}s`;
        if (duration < 3600) return `${Math.floor(duration / 60)}m ${duration % 60}s`;
        return `${Math.floor(duration / 3600)}h ${Math.floor((duration % 3600) / 60)}m`;
    };

    return (
        <div className="execution-list-container">
            <h2>Script Executions</h2>

            {showToast && (
                <div className={`toast toast-${showToast.type}`}>
                    {showToast.type === 'success' && '✓ '}
                    {showToast.type === 'error' && '✗ '}
                    {showToast.type === 'info' && 'ℹ '}
                    {showToast.message}
                </div>
            )}

            {executions && executions.length === 0 ? (
                <div className="empty-state">
                    <p>No executions yet. Execute a script to see it here!</p>
                </div>
            ) : (
                <table className="execution-table">
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Script ID</th>
                            <th>Status</th>
                            <th>Started At</th>
                            <th>Duration</th>
                            <th>Executed By</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {executions?.map((execution: Execution) => (
                            <tr key={execution.id}>
                                <td>{execution.id}</td>
                                <td>{execution.script_id}</td>
                                <td>
                                    <span
                                        className="status-badge"
                                        style={{
                                            backgroundColor: getStatusColor(execution.status),
                                            color: 'white',
                                            padding: '4px 8px',
                                            borderRadius: '4px',
                                            fontSize: '12px'
                                        }}
                                    >
                                        {getStatusIcon(execution.status)} {execution.status}
                                    </span>
                                </td>
                                <td>{execution.started_at ? formatDate(execution.started_at) : '-'}</td>
                                <td>{calculateDuration(execution)}</td>
                                <td>{execution.executed_by || user?.username || 'system'}</td>
                                <td>
                                    <button
                                        className="btn-small"
                                        onClick={() => handleViewDetails(execution)}
                                    >
                                        📄 View Details
                                    </button>
                                    {(execution.status === 'running' || execution.status === 'pending') && (
                                        <button
                                            className="btn-small btn-cancel"
                                            onClick={() => handleCancelExecution(execution.id)}
                                            style={{ marginLeft: '0.5rem' }}
                                        >
                                            ⛔ Cancel
                                        </button>
                                    )}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            )}

            {/* FIXED: Complete Execution Details Modal */}
            {selectedExecution && (
                <div className="modal-overlay" onClick={handleCloseModal}>
                    <div className="modal-details" onClick={(e) => e.stopPropagation()}>
                        <div className="modal-details-header">
                            <h2>Execution Details</h2>
                            <button className="modal-close-btn" onClick={handleCloseModal}>×</button>
                        </div>

                        <div className="modal-details-body">
                            {/* General Information Section */}
                            <div className="details-section">
                                <h3>General Information</h3>
                                <div className="details-info-grid">
                                    <div className="detail-field">
                                        <span className="detail-label">EXECUTION ID:</span>
                                        <span className="detail-value">{selectedExecution.id}</span>
                                    </div>
                                    <div className="detail-field">
                                        <span className="detail-label">SCRIPT ID:</span>
                                        <span className="detail-value">{selectedExecution.script_id}</span>
                                    </div>
                                    <div className="detail-field">
                                        <span className="detail-label">STATUS:</span>
                                        <span
                                            className="status-badge-large"
                                            style={{
                                                backgroundColor: getStatusColor(selectedExecution.status),
                                                color: 'white'
                                            }}
                                        >
                                            {getStatusIcon(selectedExecution.status)} {selectedExecution.status.toUpperCase()}
                                        </span>
                                    </div>
                                    <div className="detail-field">
                                        <span className="detail-label">EXECUTED BY:</span>
                                        <span className="detail-value">
                                            {selectedExecution.executed_by || user?.username || 'system'}
                                        </span>
                                    </div>
                                    <div className="detail-field">
                                        <span className="detail-label">CREATED AT:</span>
                                        <span className="detail-value">{formatDate(selectedExecution.created_at)}</span>
                                    </div>
                                    <div className="detail-field">
                                        <span className="detail-label">STARTED AT:</span>
                                        <span className="detail-value">
                                            {selectedExecution.started_at ? formatDate(selectedExecution.started_at) : 'Not started'}
                                        </span>
                                    </div>
                                    <div className="detail-field">
                                        <span className="detail-label">COMPLETED AT:</span>
                                        <span className="detail-value">
                                            {selectedExecution.completed_at ? formatDate(selectedExecution.completed_at) : 'Not completed'}
                                        </span>
                                    </div>
                                    <div className="detail-field">
                                        <span className="detail-label">DURATION:</span>
                                        <span className="detail-value">{calculateDuration(selectedExecution)}</span>
                                    </div>
                                </div>
                            </div>

                            {/* Parameters Section */}
                            {selectedExecution.parameters && Object.keys(selectedExecution.parameters).length > 0 && (
                                <div className="details-section">
                                    <h3>Parameters</h3>
                                    <div className="details-code-block">
                                        <pre>{JSON.stringify(selectedExecution.parameters, null, 2)}</pre>
                                    </div>
                                </div>
                            )}

                            {/* Output Section */}
                            <div className="details-section">
                                <div className="output-section-header">
                                    <h3>Output</h3>
                                    {isConnected && selectedExecution.status === 'running' && (
                                        <span className="live-indicator">
                                            <span className="live-dot"></span>
                                            Live
                                        </span>
                                    )}
                                </div>
                                <div className="details-output-block" ref={logContainerRef}>
                                    <pre>{liveLog || 'No output available'}</pre>
                                </div>
                            </div>

                            {/* Error Section */}
                            {selectedExecution.error && (
                                <div className="details-section">
                                    <h3>Error</h3>
                                    <div className="details-error-block">
                                        <pre>{selectedExecution.error}</pre>
                                    </div>
                                </div>
                            )}
                        </div>

                        <div className="modal-details-footer">
                            <label className="auto-scroll-label">
                                <input
                                    type="checkbox"
                                    checked={autoScroll}
                                    onChange={(e) => setAutoScroll(e.target.checked)}
                                />
                                Auto-scroll
                            </label>
                            <button className="btn-modal-close" onClick={handleCloseModal}>
                                Close
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default ExecutionList;