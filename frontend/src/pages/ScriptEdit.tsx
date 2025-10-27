import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate, useParams } from 'react-router-dom';
import { scriptApi, Script } from '../services/api';
import '../styles/ScriptForm.css';

const ScriptEdit: React.FC = () => {
    const { id } = useParams<{ id: string }>();
    const navigate = useNavigate();
    const queryClient = useQueryClient();
    const [showToast, setShowToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);

    const [formData, setFormData] = useState<Partial<Script>>({
        name: '',
        description: '',
        script_type: 'bash',
        content: '',
        version: '1.0.0',
        tags: [],
    });

    const [tagInput, setTagInput] = useState('');

    // Fetch existing script data
    const { data: script, isLoading } = useQuery({
        queryKey: ['script', id],
        queryFn: async () => {
            const response = await scriptApi.getById(Number(id));
            return response.data;
        },
        // onSuccess: (data) => {
        //     setFormData({
        //         name: data.name,
        //         description: data.description,
        //         script_type: data.script_type,
        //         content: data.content,
        //         version: data.version,
        //         tags: data.tags || [],
        //     });
        // },
    });

    useEffect(() => {
        if (script) {
            setFormData({
                name: script.name,
                description: script.description,
                script_type: script.script_type,
                content: script.content,
                version: script.version,
                tags: script.tags || [],
            });
        }
    }, [script]);

    const updateMutation = useMutation({
        mutationFn: (data: Partial<Script>) => scriptApi.update(Number(id), data),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['scripts'] });
            queryClient.invalidateQueries({ queryKey: ['script', id] });
            showNotification('Script updated successfully!', 'success');
            setTimeout(() => navigate(`/scripts/${id}`), 1500);
        },
        onError: (error: any) => {
            showNotification(error.response?.data?.detail || 'Failed to update script', 'error');
        },
    });

    const showNotification = (message: string, type: 'success' | 'error') => {
        setShowToast({ message, type });
        setTimeout(() => setShowToast(null), 3000);
    };

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        updateMutation.mutate(formData);
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

    if (isLoading) return <div className="loading">Loading script...</div>;

    return (
        <div className="script-form-container">
            {showToast && (
                <div className={`toast toast-${showToast.type}`}>
                    {showToast.type === 'success' && '✓ '}
                    {showToast.type === 'error' && '✗ '}
                    {showToast.message}
                </div>
            )}

            <div className="form-header">
                <button className="btn-back" onClick={() => navigate(`/scripts/${id}`)}>
                    ← Back
                </button>
                <h2>Edit Script</h2>
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
                        onClick={() => navigate(`/scripts/${id}`)}
                        className="btn-secondary"
                    >
                        Cancel
                    </button>
                    <button
                        type="submit"
                        className="btn-primary"
                        disabled={updateMutation.isPending}
                    >
                        {updateMutation.isPending ? 'Updating...' : 'Update Script'}
                    </button>
                </div>
            </form>
        </div>
    );
};

export default ScriptEdit;