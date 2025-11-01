import React from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import './Navbar.css';

const Navbar: React.FC = () => {
    const { user, logout, isAuthenticated, isAdmin } = useAuth();

    if (!isAuthenticated) return null;

    return (
        <nav className="navbar" role="navigation" aria-label="Main navigation">
            <div className="nav-brand">
                <Link to="/" className="brand-link">
                    <span className="brand-icon" aria-hidden="true">🔧</span>
                    <span className="brand-text">OpsCraft</span>
                </Link>
            </div>

            <ul className="nav-links" role="menubar">
                <li role="none">
                    <Link to="/" role="menuitem">Dashboard</Link>
                </li>
                <li role="none">
                    <Link to="/scripts" role="menuitem">Scripts</Link>
                </li>
                <li role="none">
                    <Link to="/executions" role="menuitem">Executions</Link>
                </li>
                <li role="none">
                    <Link to="/secrets" role="menuitem">Secrets</Link>
                </li>
                {isAdmin && (
                    <li role="none">
                        <Link to="/admin" role="menuitem">Admin</Link>
                    </li>
                )}
            </ul>

            <div className="nav-user">
                <div className="user-profile">
                    <div className="user-avatar" aria-hidden="true">
                        {user?.username.charAt(0).toUpperCase()}
                    </div>
                    <div className="user-details">
                        <span className="user-name">{user?.username}</span>
                        <span className="user-role">{user?.role}</span>
                    </div>
                </div>
                <button
                    onClick={logout}
                    className="btn-logout"
                    aria-label="Logout"
                >
                    <span className="logout-icon" aria-hidden="true">🚪</span>
                    <span>Logout</span>
                </button>
            </div>
        </nav>
    );
};

export default Navbar;