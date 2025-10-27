import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { scriptApi, Script } from '../services/api';
import '../styles/ScriptList.css';

const ScriptList: React.FC = () => {
    const navigate = useNavigate();

    const { data: scripts, isLoading, error } = useQuery({
        queryKey: ['scripts'],
        queryFn: async () => {
            const response = await scriptApi.getAll();
            return response.data;
        },
    });

    if (isLoading) return <div className="loading">Loading scripts...</div>;
    if (error) return <div className="error">Error loading scripts: {(error as Error).message}</div>;

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'active': return 'green';
            case 'deprecated': return 'orange';
            case 'draft': return 'gray';
            default: return 'black';
        }
    };

    const getTypeIcon = (type: string) => {
        switch (type) {
            case 'bash': return '🐚';
            case 'python': return '🐍';
            case 'ansible': return '📦';
            case 'terraform': return '🏗️';
            default: return '📄';
        }
    };

    return (
        <div className="script-list-container">
            <div className="header">
                <h2>Scripts</h2>
                <button
                    className="btn-primary"
                    onClick={() => navigate('/scripts/new')}
                >
                    + Create New Script
                </button>
            </div>

            {scripts && scripts.length === 0 ? (
                <div className="empty-state">
                    <p>No scripts found. Create your first script to get started!</p>
                </div>
            ) : (
                <div className="script-grid">
                    {scripts?.map((script: Script) => (
                        <div
                            key={script.id}
                            className="script-card"
                            onClick={() => navigate(`/scripts/${script.id}`)}
                        >
                            <div className="script-card-header">
                                <span className="script-type">{getTypeIcon(script.script_type)}</span>
                                <span
                                    className="script-status"
                                    style={{ color: getStatusColor(script.status) }}
                                >
                                    {script.status}
                                </span>
                            </div>

                            <h3>{script.name}</h3>

                            <p className="script-description">
                                {script.description || 'No description provided'}
                            </p>

                            <div className="script-meta">
                                <span className="version">v{script.version}</span>
                                <span className="type-badge">{script.script_type}</span>
                            </div>

                            {script.tags && script.tags.length > 0 && (
                                <div className="tags">
                                    {script.tags.map((tag, idx) => (
                                        <span key={idx} className="tag">{tag}</span>
                                    ))}
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
};

export default ScriptList;