import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import '../styles/Secrets.css';

const API_URL = process.env.REACT_APP_API_URL;

interface Secret {
    id: number;
    name: string;
    description?: string;
    created_by?: number;
    created_at: string;
    updated_at?: string;
    last_accessed_at?: string;
}

const SecretsManagement: React.FC = () => {
    const queryClient = useQueryClient();
    const [showCreateModal, setShowCreateModal] = useState(false);
    const [showDeleteModal, setShowDeleteModal] = useState(false);
    const [selectedSecret, setSelectedSecret] = useState<Secret | null>(null);
    const [secretName, setSecretName] = useState('');
    const [secretValue, setSecretValue] = useState('');
    const [secretDescription, setSecretDescription] = useState('');
    const [showValue, setShowValue] = useState(false);

    // Fetch secrets
    const { data: secrets, isLoading, error } = useQuery({
        queryKey: ['secrets'],
        queryFn: async () => {
            const response = await axios.get(`${API_URL}/secrets`);
            return response.data;
        },
    });

    // Create secret mutation
    const createSecretMutation = useMutation({
        mutationFn: async (data: { name: string; value: string; description?: string }) => {
            return axios.post(`${API_URL}/secrets`, data);
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['secrets'] });
            setShowCreateModal(false);
            resetForm();
        },
    });

    // Delete secret mutation
    const deleteSecretMutation = useMutation({
        mutationFn: async (id: number) => {
            return axios.delete(`${API_URL}/secrets/${id}`);
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['secrets'] });
            setShowDeleteModal(false);
            setSelectedSecret(null);
        },
    });

    const resetForm = () => {
        setSecretName('');
        setSecretValue('');
        setSecretDescription('');
        setShowValue(false);
    };

    const handleCreateSecret = () => {
        if (!secretName || !secretValue) return;

        createSecretMutation.mutate({
            name: secretName,
            value: secretValue,
            description: secretDescription || undefined,
        });
    };

    const handleDeleteClick = (secret: Secret) => {
        setSelectedSecret(secret);
        setShowDeleteModal(true);
    };

    const handleDeleteConfirm = () => {
        if (selectedSecret) {
            deleteSecretMutation.mutate(selectedSecret.id);
        }
    };

    if (isLoading) return <div className="loading">Loading secrets...</div>;
    if (error) return <div className="error">Error loading secrets</div>;

    return (
        <div className="secrets-container">
            <div className="secrets-header">
                <div>
                    <h1>🔒 Secrets Management</h1>
                    <p>Securely store and manage environment variables and secrets</p>
                </div>
                <button
                    className="btn-primary"
                    onClick={() => setShowCreateModal(true)}
                >
                    + Add Secret
                </button>
            </div>

            <div className="secrets-info">
                <div className="info-card">
                    <span className="info-icon">🔐</span>
                    <div>
                        <h3>Encrypted Storage</h3>
                        <p>All secrets are encrypted with AES-256</p>
                    </div>
                </div>
                <div className="info-card">
                    <span className="info-icon">🔑</span>
                    <div>
                        <h3>Runtime Injection</h3>
                        <p>Secrets are injected securely at execution time</p>
                    </div>
                </div>
                <div className="info-card">
                    <span className="info-icon">📝</span>
                    <div>
                        <h3>Audit Logged</h3>
                        <p>All secret access is tracked and logged</p>
                    </div>
                </div>
            </div>

            {secrets && secrets.length === 0 ? (
                <div className="empty-state">
                    <span className="empty-icon">🔒</span>
                    <h3>No Secrets Yet</h3>
                    <p>Create your first secret to store sensitive data securely</p>
                    <button
                        className="btn-primary"
                        onClick={() => setShowCreateModal(true)}
                    >
                        Create Secret
                    </button>
                </div>
            ) : (
                <div className="secrets-grid">
                    {secrets?.map((secret: Secret) => (
                        <div key={secret.id} className="secret-card">
                            <div className="secret-header">
                                <h3>🔑 {secret.name}</h3>
                                <button
                                    className="btn-icon btn-danger-icon"
                                    onClick={() => handleDeleteClick(secret)}
                                    title="Delete secret"
                                >
                                    🗑️
                                </button>
                            </div>

                            {secret.description && (
                                <p className="secret-description">{secret.description}</p>
                            )}

                            <div className="secret-meta">
                                <div className="meta-item">
                                    <span className="meta-label">Created:</span>
                                    <span>{new Date(secret.created_at).toLocaleDateString()}</span>
                                </div>
                                {secret.last_accessed_at && (
                                    <div className="meta-item">
                                        <span className="meta-label">Last Used:</span>
                                        <span>{new Date(secret.last_accessed_at).toLocaleDateString()}</span>
                                    </div>
                                )}
                            </div>

                            <div className="secret-value-section">
                                <span className="value-label">Value:</span>
                                <code className="secret-value">••••••••••••••••</code>
                                <span className="hidden-badge">Hidden</span>
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {/* Create Secret Modal */}
            {showCreateModal && (
                <div className="modal-overlay" onClick={() => setShowCreateModal(false)}>
                    <div className="modal" onClick={(e) => e.stopPropagation()}>
                        <div className="modal-header">
                            <h2>Create New Secret</h2>
                            <button className="btn-close" onClick={() => setShowCreateModal(false)}>
                                ×
                            </button>
                        </div>

                        <div className="modal-body">
                            <div className="form-group">
                                <label htmlFor="secret-name">
                                    Secret Name <span className="required">*</span>
                                </label>
                                <input
                                    id="secret-name"
                                    type="text"
                                    value={secretName}
                                    onChange={(e) => setSecretName(e.target.value)}
                                    placeholder="e.g., API_KEY, DATABASE_PASSWORD"
                                    className="form-control"
                                    autoFocus
                                />
                                <small>Use uppercase with underscores (e.g., MY_SECRET_KEY)</small>
                            </div>

                            <div className="form-group">
                                <label htmlFor="secret-value">
                                    Secret Value <span className="required">*</span>
                                </label>
                                <div className="password-input-group">
                                    <input
                                        id="secret-value"
                                        type={showValue ? 'text' : 'password'}
                                        value={secretValue}
                                        onChange={(e) => setSecretValue(e.target.value)}
                                        placeholder="Enter secret value"
                                        className="form-control"
                                    />
                                    <button
                                        type="button"
                                        className="btn-toggle-password"
                                        onClick={() => setShowValue(!showValue)}
                                    >
                                        {showValue ? '🙈' : '👁️'}
                                    </button>
                                </div>
                            </div>

                            <div className="form-group">
                                <label htmlFor="secret-description">Description</label>
                                <textarea
                                    id="secret-description"
                                    value={secretDescription}
                                    onChange={(e) => setSecretDescription(e.target.value)}
                                    placeholder="What is this secret used for?"
                                    className="form-control"
                                    rows={3}
                                />
                            </div>

                            <div className="alert alert-warning">
                                <span>⚠️</span>
                                <div>
                                    <strong>Important:</strong>
                                    <p>
                                        Secrets are encrypted and cannot be retrieved after creation.
                                        Make sure you have a backup copy if needed.
                                    </p>
                                </div>
                            </div>
                        </div>

                        <div className="modal-footer">
                            <button
                                className="btn-secondary"
                                onClick={() => setShowCreateModal(false)}
                            >
                                Cancel
                            </button>
                            <button
                                className="btn-primary"
                                onClick={handleCreateSecret}
                                disabled={!secretName || !secretValue || createSecretMutation.isPending}
                            >
                                {createSecretMutation.isPending ? 'Creating...' : 'Create Secret'}
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Delete Confirmation Modal */}
            {showDeleteModal && selectedSecret && (
                <div className="modal-overlay" onClick={() => setShowDeleteModal(false)}>
                    <div className="modal modal-danger" onClick={(e) => e.stopPropagation()}>
                        <div className="modal-header">
                            <h2>Delete Secret</h2>
                            <button className="btn-close" onClick={() => setShowDeleteModal(false)}>
                                ×
                            </button>
                        </div>

                        <div className="modal-body">
                            <div className="alert alert-error">
                                <span>⚠️</span>
                                <div>
                                    <strong>Warning!</strong>
                                    <p>
                                        You are about to delete the secret <strong>"{selectedSecret.name}"</strong>.
                                        This action cannot be undone.
                                    </p>
                                </div>
                            </div>

                            <p>Scripts using this secret will fail to execute. Make sure no scripts depend on it.</p>
                        </div>

                        <div className="modal-footer">
                            <button
                                className="btn-secondary"
                                onClick={() => setShowDeleteModal(false)}
                            >
                                Cancel
                            </button>
                            <button
                                className="btn-danger"
                                onClick={handleDeleteConfirm}
                                disabled={deleteSecretMutation.isPending}
                            >
                                {deleteSecretMutation.isPending ? 'Deleting...' : 'Delete Secret'}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default SecretsManagement;