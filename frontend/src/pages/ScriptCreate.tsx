import React, { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { scriptApi, ScriptCreate } from '../services/api';
import '../styles/ScriptForm.css';

const ScriptCreatePage: React.FC = () => {
    const navigate = useNavigate();
    const queryClient = useQueryClient();
    const [showToast, setShowToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);

    const [formData, setFormData] = useState<ScriptCreate>({
        name: '',
        description: '',
        script_type: 'bash',
        content: '',
        version: '1.0.0',
        tags: [],
    });

    const [tagInput, setTagInput] = useState('');

    const showNotification = (message: string, type: 'success' | 'error') => {
        setShowToast({ message, type });
        setTimeout(() => setShowToast(null), 3000);
    };

    const createMutation = useMutation({
        mutationFn: (data: ScriptCreate) => scriptApi.create(data),
        onSuccess: (response) => {
            queryClient.invalidateQueries({ queryKey: ['scripts'] });
            showNotification('Script created successfully!', 'success');
            setTimeout(() => navigate(`/scripts/${response.data.id}`), 1500);
        },
        onError: (error: any) => {
            showNotification(error.response?.data?.detail || 'Failed to create script', 'error');
        },
    });

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        createMutation.mutate(formData);
    };

    const handleAddTag = () => {
        if (tagInput.trim() && !formData.tags?.includes(tagInput.trim())) {
            setFormData({
                ...formData,
                tags: [...(formData.tags || []), tagInput.trim()],
            });
            setTagInput('');
        }
    };

    const handleRemoveTag = (tag: string) => {
        setFormData({
            ...formData,
            tags: formData.tags?.filter(t => t !== tag),
        });
    };

    return (
        <div className="script-form-container">
            {/* Toast Notification */}
            {showToast && (
                <div className={`toast toast-${showToast.type}`}>
                    {showToast.type === 'success' && '✓ '}
                    {showToast.type === 'error' && '✗ '}
                    {showToast.message}
                </div>
            )}

            <div className="form-header">
                <button className="btn-back" onClick={() => navigate('/scripts')}>
                    ← Back
                </button>
                <h2>Create New Script</h2>
            </div>

            <form onSubmit={handleSubmit} className="script-form">
                <div className="form-group">
                    <label htmlFor="name">Name *</label>
                    <input
                        id="name"
                        type="text"
                        value={formData.name}
                        onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                        required
                        placeholder="my-deployment-script"
                    />
                </div>

                <div className="form-group">
                    <label htmlFor="description">Description</label>
                    <textarea
                        id="description"
                        value={formData.description}
                        onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                        rows={3}
                        placeholder="What does this script do?"
                    />
                </div>

                <div className="form-row">
                    <div className="form-group">
                        <label htmlFor="script_type">Script Type *</label>
                        <select
                            id="script_type"
                            value={formData.script_type}
                            onChange={(e) => setFormData({
                                ...formData,
                                script_type: e.target.value as any
                            })}
                            required
                        >
                            <option value="bash">Bash</option>
                            <option value="python">Python</option>
                            <option value="ansible">Ansible</option>
                            <option value="terraform">Terraform</option>
                        </select>
                    </div>

                    <div className="form-group">
                        <label htmlFor="version">Version</label>
                        <input
                            id="version"
                            type="text"
                            value={formData.version}
                            onChange={(e) => setFormData({ ...formData, version: e.target.value })}
                            placeholder="1.0.0"
                        />
                    </div>
                </div>

                <div className="form-group">
                    <label htmlFor="content">Script Content *</label>
                    <textarea
                        id="content"
                        value={formData.content}
                        onChange={(e) => setFormData({ ...formData, content: e.target.value })}
                        rows={15}
                        required
                        placeholder="#!/bin/bash&#10;echo 'Hello World'"
                        className="code-editor"
                    />
                </div>

                <div className="form-group">
                    <label>Tags</label>
                    <div className="tag-input-container">
                        <input
                            type="text"
                            value={tagInput}
                            onChange={(e) => setTagInput(e.target.value)}
                            onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), handleAddTag())}
                            placeholder="Add a tag and press Enter"
                        />
                        <button
                            type="button"
                            onClick={handleAddTag}
                            className="btn-secondary"
                        >
                            Add
                        </button>
                    </div>
                    {formData.tags && formData.tags.length > 0 && (
                        <div className="tags-display">
                            {formData.tags.map((tag, idx) => (
                                <span key={idx} className="tag">
                                    {tag}
                                    <button
                                        type="button"
                                        onClick={() => handleRemoveTag(tag)}
                                        className="tag-remove"
                                    >
                                        ×
                                    </button>
                                </span>
                            ))}
                        </div>
                    )}
                </div>

                <div className="form-actions">
                    <button
                        type="button"
                        onClick={() => navigate('/scripts')}
                        className="btn-secondary"
                    >
                        Cancel
                    </button>
                    <button
                        type="submit"
                        className="btn-primary"
                        disabled={createMutation.isPending}
                    >
                        {createMutation.isPending ? 'Creating...' : 'Create Script'}
                    </button>
                </div>
            </form>
        </div>
    );
};

export default ScriptCreatePage;