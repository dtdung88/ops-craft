import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useParams, useNavigate } from 'react-router-dom';
import { scriptApi, executionApi, secretsApi } from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import '../styles/ScriptDetail.css';

interface Secret {
    id: number;
    name: string;
    description?: string;
    created_at: string;
}

interface AuditLog {
    id: number;
    action: string;
    accessed_by: number;
    accessed_by_username: string;
    execution_id?: number;
    script_id?: number;
    timestamp: string;
}

const ScriptDetail: React.FC = () => {
    const { id } = useParams<{ id: string }>();
    const navigate = useNavigate();
    const queryClient = useQueryClient();
    const { isOperator, isAdmin } = useAuth();
    const [showExecuteModal, setShowExecuteModal] = useState(false);
    const [showSecretsModal, setShowSecretsModal] = useState(false);
    const [showAuditModal, setShowAuditModal] = useState(false);
    const [selectedSecretForAudit, setSelectedSecretForAudit] = useState<Secret | null>(null);
    const [parameters, setParameters] = useState('{}');
    const [showToast, setShowToast] = useState<{ message: string; type: 'success' | 'error' | 'info' } | null>(null);

    const { data: script, isLoading, error } = useQuery({
        queryKey: ['script', id],
        queryFn: async () => {
            const response = await scriptApi.getById(Number(id));
            return response.data;
        },
    });

    const { data: attachedSecrets, refetch: refetchSecrets } = useQuery({
        queryKey: ['script-secrets', id],
        queryFn: async () => {
            const response = await scriptApi.getSecrets(Number(id));
            return response.data;
        },
    });

    const { data: allSecrets } = useQuery({
        queryKey: ['all-secrets'],
        queryFn: async () => {
            const response = await secretsApi.getAll();
            return response.data;
        },
        enabled: showSecretsModal,
    });

    const { data: auditLogs } = useQuery({
        queryKey: ['secret-audit', selectedSecretForAudit?.id],
        queryFn: async () => {
            if (!selectedSecretForAudit?.id) return [];
            const response = await secretsApi.getAuditLogs(selectedSecretForAudit.id);
            return response.data;
        },
        enabled: !!selectedSecretForAudit,
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

    const attachSecretMutation = useMutation({
        mutationFn: async (secretId: number) => {
            return scriptApi.attachSecret(Number(id), secretId);
        },
        onSuccess: () => {
            refetchSecrets();
            showNotification('Secret attached successfully', 'success');
        },
        onError: () => {
            showNotification('Failed to attach secret', 'error');
        },
    });

    const detachSecretMutation = useMutation({
        mutationFn: async (secretId: number) => {
            return scriptApi.detachSecret(Number(id), secretId);
        },
        onSuccess: () => {
            refetchSecrets();
            showNotification('Secret detached successfully', 'success');
        },
        onError: () => {
            showNotification('Failed to detach secret', 'error');
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

    const handleViewAudit = (secret: Secret) => {
        setSelectedSecretForAudit(secret);
        setShowAuditModal(true);
    };

    const handleCloseAuditModal = () => {
        setShowAuditModal(false);
        setTimeout(() => setSelectedSecretForAudit(null), 300);
    };

    if (isLoading) return <div className="loading">Loading script...</div>;
    if (error) return <div className="error">Error loading script: {(error as Error).message}</div>;
    if (!script) return <div className="error">Script not found</div>;

    const availableSecrets = allSecrets?.filter(
        (secret: Secret) => !attachedSecrets?.some((attached: Secret) => attached.id === secret.id)
    ) || [];

    return (
        <div className="script-detail-container">
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
                        <>
                            <button className="btn-edit" onClick={() => navigate(`/scripts/${id}/edit`)}>
                                ✏️ Edit
                            </button>
                            <button className="btn-secrets" onClick={() => setShowSecretsModal(true)}>
                                🔐 Manage Secrets
                            </button>
                        </>
                    )}
                    <button className="btn-primary" onClick={() => setShowExecuteModal(true)}>
                        ▶ Execute
                    </button>
                    {(isOperator || isAdmin) && (
                        <button className="btn-danger" onClick={handleDelete} disabled={deleteMutation.isPending}>
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

                {script.description && <p className="description">{script.description}</p>}

                {script.tags && script.tags.length > 0 && (
                    <div className="tags">
                        {script.tags.map((tag, idx) => (
                            <span key={idx} className="tag">{tag}</span>
                        ))}
                    </div>
                )}
            </div>

            {attachedSecrets && attachedSecrets.length > 0 && (
                <div className="attached-secrets-section">
                    <h3>🔐 Attached Secrets ({attachedSecrets.length})</h3>
                    <div className="secrets-list">
                        {attachedSecrets.map((secret: Secret) => (
                            <div key={secret.id} className="secret-item">
                                <span className="secret-name">🔑 {secret.name}</span>
                                <span className="secret-desc">{secret.description}</span>
                                <div className="secret-actions">
                                    <button
                                        className="btn-small-action"
                                        onClick={() => handleViewAudit(secret)}
                                        title="View audit logs"
                                    >
                                        📊 Audit
                                    </button>
                                    {(isOperator || isAdmin) && (
                                        <button
                                            className="btn-small-danger"
                                            onClick={() => detachSecretMutation.mutate(secret.id)}
                                            title="Detach secret"
                                        >
                                            ✕
                                        </button>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                    <p className="secret-notice">
                        ℹ️ These secrets will be injected as environment variables during execution
                    </p>
                </div>
            )}

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

            {/* Execute Modal */}
            {showExecuteModal && (
                <div className="modal-overlay" onClick={() => setShowExecuteModal(false)}>
                    <div className="modal" onClick={(e) => e.stopPropagation()}>
                        <div className="modal-header">
                            <h2>Execute Script</h2>
                            <button
                                className="modal-close"
                                onClick={() => setShowExecuteModal(false)}
                                aria-label="Close modal"
                            >
                                ×
                            </button>
                        </div>
                        <div className="modal-body">
                            <div className="form-group">
                                <label>Parameters (JSON):</label>
                                <textarea
                                    value={parameters}
                                    onChange={(e) => setParameters(e.target.value)}
                                    rows={10}
                                    placeholder='{"key": "value"}'
                                />
                            </div>
                        </div>
                        <div className="modal-actions">
                            <button className="btn-secondary" onClick={() => setShowExecuteModal(false)}>
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

            {/* Manage Secrets Modal */}
            {showSecretsModal && (
                <div className="modal-overlay" onClick={() => setShowSecretsModal(false)}>
                    <div className="modal-large" onClick={(e) => e.stopPropagation()}>
                        <div className="modal-header">
                            <h2>🔐 Manage Secrets</h2>
                            <button
                                className="modal-close"
                                onClick={() => setShowSecretsModal(false)}
                                aria-label="Close modal"
                            >
                                ×
                            </button>
                        </div>
                        <div className="modal-body">
                            <h3>Available Secrets</h3>
                            {availableSecrets.length === 0 ? (
                                <div className="modal-empty-state">
                                    <p>All secrets are already attached or no secrets available.</p>
                                </div>
                            ) : (
                                <div className="secrets-grid">
                                    {availableSecrets.map((secret: Secret) => (
                                        <div key={secret.id} className="secret-card-attach">
                                            <div className="secret-card-content">
                                                <strong>🔑 {secret.name}</strong>
                                                {secret.description && <p>{secret.description}</p>}
                                            </div>
                                            <button
                                                className="btn-attach"
                                                onClick={() => attachSecretMutation.mutate(secret.id)}
                                                disabled={attachSecretMutation.isPending}
                                            >
                                                + Attach
                                            </button>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            )}

            {/* Audit Logs Modal */}
            {showAuditModal && selectedSecretForAudit && (
                <div className="modal-overlay" onClick={handleCloseAuditModal}>
                    <div className="modal-large" onClick={(e) => e.stopPropagation()}>
                        <div className="modal-header">
                            <h2>📊 Audit Logs: {selectedSecretForAudit.name}</h2>
                            <button
                                className="modal-close"
                                onClick={handleCloseAuditModal}
                                aria-label="Close modal"
                            >
                                ×
                            </button>
                        </div>
                        <div className="modal-body">
                            {auditLogs && auditLogs.length > 0 ? (
                                <table className="audit-table">
                                    <thead>
                                        <tr>
                                            <th>Action</th>
                                            <th>User</th>
                                            <th>Execution ID</th>
                                            <th>Timestamp</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {auditLogs.map((log: AuditLog) => (
                                            <tr key={log.id}>
                                                <td>
                                                    <span className={`audit-action audit-${log.action.toLowerCase().replace(/_/g, '_')}`}>
                                                        {log.action.replace(/_/g, ' ')}
                                                    </span>
                                                </td>
                                                <td>{log.accessed_by}</td>
                                                <td>{log.execution_id || '-'}</td>
                                                <td>{new Date(log.timestamp).toLocaleString()}</td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            ) : (
                                <div className="modal-empty-state">
                                    <p>No audit logs available for this secret.</p>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default ScriptDetail;