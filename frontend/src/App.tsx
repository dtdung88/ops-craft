import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import Login from './pages/Login';
import Register from './pages/Register';
import ScriptList from './pages/ScriptList';
import ScriptDetail from './pages/ScriptDetail';
import ScriptCreate from './pages/ScriptCreate';
import ScriptEdit from './pages/ScriptEdit';
import ExecutionList from './pages/ExecutionList';
import Dashboard from './pages/Dashboard';
import AdminPanel from './pages/AdminPanel';
import SecretsManagement from './pages/SecretsManagement';
import './App.css';

const queryClient = new QueryClient({
    defaultOptions: {
        queries: {
            refetchOnWindowFocus: false,
            retry: 1,
        },
    },
});


const Navbar: React.FC = () => {
    const { user, logout, isAuthenticated, isAdmin } = useAuth();

    if (!isAuthenticated) return null;

    return (
        <nav className="navbar">
            <div className="nav-brand">
                <span className="brand-icon">🔧</span>
                <span className="brand-text">OpsCraft</span>
            </div>

            <ul className="nav-links">
                <li><Link to="/">Dashboard</Link></li>
                <li><Link to="/scripts">Scripts</Link></li>
                <li><Link to="/executions">Executions</Link></li>
                <li><Link to="/secrets">Secrets</Link></li>
                {isAdmin && <li><Link to="/admin">Admin</Link></li>}
            </ul>

            <div className="nav-user">
                <div className="user-profile">
                    <div className="user-avatar">
                        {user?.username.charAt(0).toUpperCase()}
                    </div>
                    <div className="user-details">
                        <span className="user-name">{user?.username}</span>
                        <span className="user-role">{user?.role}</span>
                    </div>
                </div>
                <button onClick={logout} className="btn-logout">
                    <span className="logout-icon">🚪</span>
                    <span>Logout</span>
                </button>
            </div>
        </nav>
    );
};

function App() {
    return (
        <QueryClientProvider client={queryClient}>
            <Router>
                <AuthProvider>
                    <div className="App">
                        <Navbar />
                        <main className="main-content">
                            <Routes>
                                {/* Public routes */}
                                <Route path="/login" element={<Login />} />
                                <Route path="/register" element={<Register />} />

                                {/* Protected routes */}
                                <Route
                                    path="/"
                                    element={
                                        <ProtectedRoute>
                                            <Dashboard />
                                        </ProtectedRoute>
                                    }
                                />
                                <Route
                                    path="/scripts"
                                    element={
                                        <ProtectedRoute>
                                            <ScriptList />
                                        </ProtectedRoute>
                                    }
                                />
                                <Route
                                    path="/scripts/new"
                                    element={
                                        <ProtectedRoute requireOperator>
                                            <ScriptCreate />
                                        </ProtectedRoute>
                                    }
                                />
                                <Route
                                    path="/scripts/:id"
                                    element={
                                        <ProtectedRoute>
                                            <ScriptDetail />
                                        </ProtectedRoute>
                                    }
                                />
                                <Route
                                    path="/scripts/:id/edit"
                                    element={
                                        <ProtectedRoute requireOperator>
                                            <ScriptEdit />
                                        </ProtectedRoute>
                                    }
                                />
                                <Route
                                    path="/executions"
                                    element={
                                        <ProtectedRoute>
                                            <ExecutionList />
                                        </ProtectedRoute>
                                    }
                                />
                                <Route
                                    path="/secrets"
                                    element={
                                        <ProtectedRoute requireOperator>
                                            <SecretsManagement />
                                        </ProtectedRoute>
                                    }
                                />
                                <Route
                                    path="/admin"
                                    element={
                                        <ProtectedRoute requireAdmin>
                                            <AdminPanel />
                                        </ProtectedRoute>
                                    }
                                />

                                {/* Fallback */}
                                <Route path="*" element={<Navigate to="/" replace />} />
                            </Routes>
                        </main>
                    </div>
                </AuthProvider>
            </Router>
        </QueryClientProvider>
    );
}

export default App