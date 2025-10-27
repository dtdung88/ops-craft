import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useParams, useNavigate } from 'react-router-dom';
import { scriptApi, executionApi } from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import '../styles/ScriptDetail.css';

const ScriptDetail: React.FC = () => {
    const { id } = useParams<{ id: string }>();
    const navigate = useNavigate();
    const queryClient = useQueryClient();
    const { isOperator, isAdmin } = useAuth();
    const [showExecuteModal, setShowExecuteModal] = useState(false);
    const [parameters, setParameters] = useState('{}');
    const [showToast, setShowToast] = useState<{ message: string; type: 'success' | 'error' | 'info' } | null>(null);

    const { data: script, isLoading, error } = useQuery({
        queryKey: ['script', id],
        queryFn: async () => {
            const response = await scriptApi.getById(Number(id));
            return response.data;
        },
    });

    const showNotification = (message: string, type: 'success' | 'error' | 'info') => {
        setShowToast({ message, type });
        setTimeout(() => setShowToast(null), 3000);
    };

    const deleteMutation = useMutation({
        mutationFn: () => scriptApi.delete(Number(id)),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['scripts'] });
            showNotification('Script deleted successfully', 'success');
            setTimeout(() => navigate('/scripts'), 1500);
        },
        onError: (error: any) => {
            showNotification(error.response?.data?.detail || 'Failed to delete script', 'error');
        },
    });

    const executeMutation = useMutation({
        mutationFn: (params: any) => executionApi.create({
            script_id: Number(id),
            parameters: params,
        }),
        onSuccess: () => {
            setShowExecuteModal(false);
            showNotification('Script execution started successfully!', 'success');
            setTimeout(() => navigate('/executions'), 1500);
        },
        onError: (error: any) => {
            showNotification(error.response?.data?.detail || 'Failed to execute script', 'error');
        },
    });

    const handleDelete = () => {
        if (window.confirm('Are you sure you want to delete this script? This action cannot be undone.')) {
            deleteMutation.mutate();
        }
    };

    const handleExecute = () => {
        try {
            const params = JSON.parse(parameters);
            executeMutation.mutate(params);
        } catch (e) {
            showNotification('Invalid JSON parameters', 'error');
        }
    };

    if (isLoading) return <div className="loading">Loading script...</div>;
    if (error) return <div className="error">Error loading script: {(error as Error).message}</div>;
    if (!script) return <div className="error">Script not found</div>;

    return (
        <div className="script-detail-container">
            {/* Toast Notification */}
            {showToast && (
                <div className={`toast toast-${showToast.type}`}>
                    {showToast.type === 'success' && '✓ '}
                    {showToast.type === 'error' && '✗ '}
                    {showToast.type === 'info' && 'ℹ '}
                    {showToast.message}
                </div>
            )}

            <div className="detail-header">
                <button className="btn-back" onClick={() => navigate('/scripts')}>
                    ← Back to Scripts
                </button>
                <div className="actions">
                    {(isOperator || isAdmin) && (
                        <button
                            className="btn-edit"
                            onClick={() => navigate(`/scripts/${id}/edit`)}
                        >
                            ✏️ Edit
                        </button>
                    )}
                    <button
                        className="btn-primary"
                        onClick={() => setShowExecuteModal(true)}
                    >
                        ▶ Execute
                    </button>
                    {(isOperator || isAdmin) && (
                        <button
                            className="btn-danger"
                            onClick={handleDelete}
                            disabled={deleteMutation.isPending}
                        >
                            {deleteMutation.isPending ? 'Deleting...' : 'Delete'}
                        </button>
                    )}
                </div>
            </div>

            <div className="script-info">
                <h1>{script.name}</h1>
                <div className="metadata">
                    <span className="badge">{script.script_type}</span>
                    <span className="badge version">v{script.version}</span>
                    <span className={`badge status-${script.status}`}>{script.status}</span>
                </div>

                {script.description && (
                    <p className="description">{script.description}</p>
                )}

                {script.tags && script.tags.length > 0 && (
                    <div className="tags">
                        {script.tags.map((tag, idx) => (
                            <span key={idx} className="tag">{tag}</span>
                        ))}
                    </div>
                )}
            </div>

            <div className="script-content">
                <h3>Script Content</h3>
                <pre className="code-block">
                    <code>{script.content}</code>
                </pre>
            </div>

            {script.parameters && (
                <div className="script-parameters">
                    <h3>Parameters Schema</h3>
                    <pre className="code-block">
                        <code>{JSON.stringify(script.parameters, null, 2)}</code>
                    </pre>
                </div>
            )}

            {showExecuteModal && (
                <div className="modal-overlay" onClick={() => setShowExecuteModal(false)}>
                    <div className="modal" onClick={(e) => e.stopPropagation()}>
                        <h2>Execute Script</h2>
                        <div className="form-group">
                            <label>Parameters (JSON):</label>
                            <textarea
                                value={parameters}
                                onChange={(e) => setParameters(e.target.value)}
                                rows={10}
                                placeholder='{"key": "value"}'
                            />
                        </div>
                        <div className="modal-actions">
                            <button
                                className="btn-secondary"
                                onClick={() => setShowExecuteModal(false)}
                            >
                                Cancel
                            </button>
                            <button
                                className="btn-primary"
                                onClick={handleExecute}
                                disabled={executeMutation.isPending}
                            >
                                {executeMutation.isPending ? 'Executing...' : 'Execute'}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default ScriptDetail;