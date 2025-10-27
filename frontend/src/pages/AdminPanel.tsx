import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import '../styles/AdminPanel.css';

const API_URL = process.env.REACT_APP_API_URL;

interface User {
    id: number;
    username: string;
    email: string;
    full_name?: string;
    role: string;
    is_active: boolean;
    created_at: string;
    last_login?: string;
}

const AdminPanel: React.FC = () => {
    const queryClient = useQueryClient();
    const [selectedUser, setSelectedUser] = useState<User | null>(null);
    const [showEditModal, setShowEditModal] = useState(false);

    // Fetch all users
    const { data: users, isLoading, error } = useQuery({
        queryKey: ['users'],
        queryFn: async () => {
            const response = await axios.get(`${API_URL}/admin/users`);
            return response.data;
        },
    });

    // Update user mutation
    const updateUserMutation = useMutation({
        mutationFn: async (userData: { id: number; role?: string; is_active?: boolean }) => {
            const { id, ...data } = userData;
            return axios.put(`${API_URL}/admin/users/${id}`, data);
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['users'] });
            setShowEditModal(false);
            setSelectedUser(null);
        },
    });

    // Delete user mutation
    const deleteUserMutation = useMutation({
        mutationFn: async (userId: number) => {
            return axios.delete(`${API_URL}/admin/users/${userId}`);
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['users'] });
        },
    });

    const handleEditUser = (user: User) => {
        setSelectedUser(user);
        setShowEditModal(true);
    };

    const handleUpdateUser = (role: string, isActive: boolean) => {
        if (!selectedUser) return;

        updateUserMutation.mutate({
            id: selectedUser.id,
            role,
            is_active: isActive,
        });
    };

    const handleDeleteUser = (userId: number, username: string) => {
        if (window.confirm(`Are you sure you want to delete user "${username}"?`)) {
            deleteUserMutation.mutate(userId);
        }
    };

    const getRoleBadgeClass = (role: string) => {
        switch (role) {
            case 'admin': return 'badge-admin';
            case 'operator': return 'badge-operator';
            case 'viewer': return 'badge-viewer';
            default: return 'badge-default';
        }
    };

    if (isLoading) return <div className="loading">Loading users...</div>;
    if (error) return <div className="error">Error loading users</div>;

    return (
        <div className="admin-panel">
            <div className="panel-header">
                <h1>👥 User Management</h1>
                <p>Manage users, roles, and permissions</p>
            </div>

            <div className="stats-row">
                <div className="stat-card">
                    <span className="stat-icon">👤</span>
                    <div>
                        <h3>{users?.length || 0}</h3>
                        <p>Total Users</p>
                    </div>
                </div>
                <div className="stat-card">
                    <span className="stat-icon">👑</span>
                    <div>
                        <h3>{users?.filter((u: User) => u.role === 'admin').length || 0}</h3>
                        <p>Admins</p>
                    </div>
                </div>
                <div className="stat-card">
                    <span className="stat-icon">⚙️</span>
                    <div>
                        <h3>{users?.filter((u: User) => u.role === 'operator').length || 0}</h3>
                        <p>Operators</p>
                    </div>
                </div>
                <div className="stat-card">
                    <span className="stat-icon">👁️</span>
                    <div>
                        <h3>{users?.filter((u: User) => u.role === 'viewer').length || 0}</h3>
                        <p>Viewers</p>
                    </div>
                </div>
            </div>

            <div className="users-table-container">
                <table className="users-table">
                    <thead>
                        <tr>
                            <th>User</th>
                            <th>Email</th>
                            <th>Role</th>
                            <th>Status</th>
                            <th>Last Login</th>
                            <th>Joined</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {users?.map((user: User) => (
                            <tr key={user.id}>
                                <td>
                                    <div className="user-info">
                                        <div className="user-avatar">
                                            {user.username.charAt(0).toUpperCase()}
                                        </div>
                                        <div>
                                            <strong>{user.username}</strong>
                                            {user.full_name && <small>{user.full_name}</small>}
                                        </div>
                                    </div>
                                </td>
                                <td>{user.email}</td>
                                <td>
                                    <span className={`badge ${getRoleBadgeClass(user.role)}`}>
                                        {user.role}
                                    </span>
                                </td>
                                <td>
                                    <span className={`status-badge ${user.is_active ? 'active' : 'inactive'}`}>
                                        {user.is_active ? 'Active' : 'Inactive'}
                                    </span>
                                </td>
                                <td>
                                    {user.last_login
                                        ? new Date(user.last_login).toLocaleDateString()
                                        : 'Never'}
                                </td>
                                <td>{new Date(user.created_at).toLocaleDateString()}</td>
                                <td>
                                    <div className="action-buttons">
                                        <button
                                            className="btn-icon"
                                            onClick={() => handleEditUser(user)}
                                            title="Edit user"
                                        >
                                            ✏️
                                        </button>
                                        <button
                                            className="btn-icon btn-danger"
                                            onClick={() => handleDeleteUser(user.id, user.username)}
                                            title="Delete user"
                                        >
                                            🗑️
                                        </button>
                                    </div>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            {/* Edit User Modal */}
            {showEditModal && selectedUser && (
                <div className="modal-overlay" onClick={() => setShowEditModal(false)}>
                    <div className="modal" onClick={(e) => e.stopPropagation()}>
                        <div className="modal-header">
                            <h2>Edit User: {selectedUser.username}</h2>
                            <button className="btn-close" onClick={() => setShowEditModal(false)}>
                                ×
                            </button>
                        </div>

                        <div className="modal-body">
                            <div className="form-group">
                                <label>Role</label>
                                <select
                                    defaultValue={selectedUser.role}
                                    id="role-select"
                                    className="form-control"
                                >
                                    <option value="admin">Admin - Full Access</option>
                                    <option value="operator">Operator - Create & Execute</option>
                                    <option value="viewer">Viewer - Read Only</option>
                                </select>
                            </div>

                            <div className="form-group">
                                <label className="checkbox-label">
                                    <input
                                        type="checkbox"
                                        defaultChecked={selectedUser.is_active}
                                        id="active-checkbox"
                                    />
                                    <span>Account Active</span>
                                </label>
                            </div>

                            <div className="info-box">
                                <h4>Role Permissions:</h4>
                                <ul>
                                    <li><strong>Admin:</strong> All permissions including user management</li>
                                    <li><strong>Operator:</strong> Create, edit, and execute scripts</li>
                                    <li><strong>Viewer:</strong> View scripts and executions only</li>
                                </ul>
                            </div>
                        </div>

                        <div className="modal-footer">
                            <button
                                className="btn-secondary"
                                onClick={() => setShowEditModal(false)}
                            >
                                Cancel
                            </button>
                            <button
                                className="btn-primary"
                                onClick={() => {
                                    const role = (document.getElementById('role-select') as HTMLSelectElement).value;
                                    const isActive = (document.getElementById('active-checkbox') as HTMLInputElement).checked;
                                    handleUpdateUser(role, isActive);
                                }}
                                disabled={updateUserMutation.isPending}
                            >
                                {updateUserMutation.isPending ? 'Saving...' : 'Save Changes'}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default AdminPanel;