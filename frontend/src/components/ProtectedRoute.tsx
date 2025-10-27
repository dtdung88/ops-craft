import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

interface ProtectedRouteProps {
    children: React.ReactNode;
    requireAdmin?: boolean;
    requireOperator?: boolean;
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
    children,
    requireAdmin = false,
    requireOperator = false,
}) => {
    const { isAuthenticated, isAdmin, isOperator, loading } = useAuth();

    if (loading) {
        return (
            <div className="loading-container">
                <div className="spinner"></div>
                <p>Loading...</p>
            </div>
        );
    }

    if (!isAuthenticated) {
        return <Navigate to="/login" replace />;
    }

    if (requireAdmin && !isAdmin) {
        return (
            <div className="unauthorized">
                <h2>Access Denied</h2>
                <p>You need administrator privileges to access this page.</p>
                <button onClick={() => window.history.back()}>Go Back</button>
            </div>
        );
    }

    if (requireOperator && !isOperator) {
        return (
            <div className="unauthorized">
                <h2>Access Denied</h2>
                <p>You need operator privileges to access this page.</p>
                <button onClick={() => window.history.back()}>Go Back</button>
            </div>
        );
    }

    return <>{children}</>;
};

export default ProtectedRoute;