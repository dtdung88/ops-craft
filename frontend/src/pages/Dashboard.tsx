import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { scriptApi, executionApi, Script, Execution } from '../services/api';
import '../styles/Dashboard.css';

const Dashboard: React.FC = () => {
    const navigate = useNavigate();

    const { data: scripts } = useQuery({
        queryKey: ['scripts'],
        queryFn: async () => {
            const response = await scriptApi.getAll();
            return response.data;
        },
    });

    const { data: executions } = useQuery({
        queryKey: ['executions'],
        queryFn: async () => {
            const response = await executionApi.getAll();
            return response.data;
        },
    });

    const stats = {
        totalScripts: scripts?.length || 0,
        activeScripts: scripts?.filter(s => s.status === 'active').length || 0,
        totalExecutions: executions?.length || 0,
        runningExecutions: executions?.filter(e => e.status === 'running').length || 0,
        successRate: executions?.length
            ? Math.round((executions.filter(e => e.status === 'success').length / executions.length) * 100)
            : 0,
        failedToday: executions?.filter(e => {
            const today = new Date().toDateString();
            return e.status === 'failed' && new Date(e.created_at).toDateString() === today;
        }).length || 0,
    };

    const recentExecutions = executions?.slice(0, 8) || [];
    const recentScripts = scripts?.slice(0, 6) || [];

    const scriptTypeColors: { [key: string]: string } = {
        bash: '#4CAF50',
        python: '#3776AB',
        ansible: '#EE0000',
        terraform: '#7B42BC',
    };

    return (
        <div className="dashboard-container-modern">
            <div className="dashboard-header">
                <div>
                    <h1>Dashboard</h1>
                    <p className="subtitle">Welcome back! Here's what's happening with your scripts.</p>
                </div>
                <button onClick={() => navigate('/scripts/new')} className="btn-primary-create">
                    <span className="icon">+</span> Create Script
                </button>
            </div>

            {/* Stats Grid */}
            <div className="stats-grid-modern">
                <div className="stat-card-modern stat-primary">
                    <div className="stat-icon">📊</div>
                    <div className="stat-content">
                        <div className="stat-label">Total Scripts</div>
                        <div className="stat-value">{stats.totalScripts}</div>
                        <div className="stat-subtitle">{stats.activeScripts} active</div>
                    </div>
                    <button onClick={() => navigate('/scripts')} className="stat-action">View All →</button>
                </div>

                <div className="stat-card-modern stat-success">
                    <div className="stat-icon">✅</div>
                    <div className="stat-content">
                        <div className="stat-label">Success Rate</div>
                        <div className="stat-value">{stats.successRate}%</div>
                        <div className="stat-subtitle">Overall performance</div>
                    </div>
                    <div className="stat-progress">
                        <div className="progress-bar" style={{ width: `${stats.successRate}%` }}></div>
                    </div>
                </div>

                <div className="stat-card-modern stat-info">
                    <div className="stat-icon">🔄</div>
                    <div className="stat-content">
                        <div className="stat-label">Total Executions</div>
                        <div className="stat-value">{stats.totalExecutions}</div>
                        <div className="stat-subtitle">{stats.runningExecutions} running now</div>
                    </div>
                    <button onClick={() => navigate('/executions')} className="stat-action">View All →</button>
                </div>

                <div className="stat-card-modern stat-warning">
                    <div className="stat-icon">⚠️</div>
                    <div className="stat-content">
                        <div className="stat-label">Failed Today</div>
                        <div className="stat-value">{stats.failedToday}</div>
                        <div className="stat-subtitle">Requires attention</div>
                    </div>
                    {stats.failedToday > 0 && (
                        <button onClick={() => navigate('/executions')} className="stat-action">Investigate →</button>
                    )}
                </div>
            </div>

            {/* Two Column Layout */}
            <div className="dashboard-grid">
                {/* Recent Executions */}
                <div className="dashboard-section">
                    <div className="section-header">
                        <h2>Recent Executions</h2>
                        <button onClick={() => navigate('/executions')} className="btn-link">
                            View All →
                        </button>
                    </div>
                    {recentExecutions.length === 0 ? (
                        <div className="empty-state-small">
                            <p>No executions yet</p>
                            <button onClick={() => navigate('/scripts')} className="btn-secondary-dash">
                                Run Your First Script
                            </button>
                        </div>
                    ) : (
                        <div className="execution-timeline">
                            {recentExecutions.map((execution) => (
                                <div key={execution.id} className="timeline-item">
                                    <div className={`timeline-indicator status-${execution.status}`}></div>
                                    <div className="timeline-content">
                                        <div className="timeline-header">
                                            <span className="timeline-title">Execution #{execution.id}</span>
                                            <span className={`status-badge-timeline status-${execution.status}`}>
                                                {execution.status}
                                            </span>
                                        </div>
                                        <div className="timeline-meta">
                                            <span>Script ID: {execution.script_id}</span>
                                            <span className="timeline-time">
                                                {new Date(execution.created_at).toLocaleString()}
                                            </span>
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>

                {/* Recent Scripts */}
                <div className="dashboard-section">
                    <div className="section-header">
                        <h2>Recent Scripts</h2>
                        <button onClick={() => navigate('/scripts')} className="btn-link">
                            View All →
                        </button>
                    </div>
                    {recentScripts.length === 0 ? (
                        <div className="empty-state-small">
                            <p>No scripts yet</p>
                            <button onClick={() => navigate('/scripts/new')} className="btn-secondary-dash">
                                Create Your First Script
                            </button>
                        </div>
                    ) : (
                        <div className="scripts-list">
                            {recentScripts.map((script) => (
                                <div
                                    key={script.id}
                                    className="script-item"
                                    onClick={() => navigate(`/scripts/${script.id}`)}
                                >
                                    <div
                                        className="script-type-indicator"
                                        style={{ backgroundColor: scriptTypeColors[script.script_type] || '#95a5a6' }}
                                    >
                                        {script.script_type.substring(0, 2).toUpperCase()}
                                    </div>
                                    <div className="script-info">
                                        <div className="script-name">{script.name}</div>
                                        <div className="script-meta">
                                            <span className="script-type">{script.script_type}</span>
                                            <span className={`script-status status-${script.status}`}>
                                                {script.status}
                                            </span>
                                        </div>
                                    </div>
                                    <div className="script-action">→</div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </div>

            {/* Quick Actions */}
            <div className="quick-actions">
                <h2>Quick Actions</h2>
                <div className="action-grid">
                    <button onClick={() => navigate('/scripts/new')} className="action-card">
                        <span className="action-icon">📝</span>
                        <span className="action-label">Create Script</span>
                    </button>
                    <button onClick={() => navigate('/scripts')} className="action-card">
                        <span className="action-icon">▶️</span>
                        <span className="action-label">Run Script</span>
                    </button>
                    <button onClick={() => navigate('/executions')} className="action-card">
                        <span className="action-icon">📋</span>
                        <span className="action-label">View Logs</span>
                    </button>
                    <button onClick={() => navigate('/secrets')} className="action-card">
                        <span className="action-icon">🔐</span>
                        <span className="action-label">Manage Secrets</span>
                    </button>
                </div>
            </div>
        </div>
    );
};

export default Dashboard;