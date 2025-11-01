import React, { createContext, useContext, useState, useCallback, ReactNode } from 'react';
import './ToastContext.css';

interface ToastMessage {
    id: string;
    message: string;
    type: 'success' | 'error' | 'info';
}

interface ToastContextType {
    showToast: (message: string, type: ToastMessage['type']) => void;
    success: (message: string) => void;
    error: (message: string) => void;
    info: (message: string) => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

interface ToastProps {
    message: string;
    type: 'success' | 'error' | 'info';
    onClose: () => void;
}

const Toast: React.FC<ToastProps> = ({ message, type, onClose }) => {
    const icons = {
        success: '✓',
        error: '✗',
        info: 'ℹ'
    };

    return (
        <div className={`toast toast-${type}`} role="alert" aria-live="polite">
            <span className="toast-icon" aria-hidden="true">{icons[type]}</span>
            <span className="toast-message">{message}</span>
            <button
                className="toast-close"
                onClick={onClose}
                aria-label="Close notification"
            >
                ×
            </button>
        </div>
    );
};

export const ToastProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
    const [toasts, setToasts] = useState<ToastMessage[]>([]);

    const showToast = useCallback((message: string, type: ToastMessage['type']) => {
        const id = Math.random().toString(36).substr(2, 9);
        setToasts(prev => [...prev, { id, message, type }]);

        // Auto-dismiss after 3 seconds
        setTimeout(() => {
            setToasts(prev => prev.filter(toast => toast.id !== id));
        }, 3000);
    }, []);

    const removeToast = useCallback((id: string) => {
        setToasts(prev => prev.filter(toast => toast.id !== id));
    }, []);

    const value = {
        showToast,
        success: (msg: string) => showToast(msg, 'success'),
        error: (msg: string) => showToast(msg, 'error'),
        info: (msg: string) => showToast(msg, 'info')
    };

    return (
        <ToastContext.Provider value={value}>
            {children}
            <div className="toast-container" aria-live="polite" aria-atomic="true">
                {toasts.map(toast => (
                    <Toast
                        key={toast.id}
                        message={toast.message}
                        type={toast.type}
                        onClose={() => removeToast(toast.id)}
                    />
                ))}
            </div>
        </ToastContext.Provider>
    );
};

export const useToast = () => {
    const context = useContext(ToastContext);
    if (!context) {
        throw new Error('useToast must be used within ToastProvider');
    }
    return context;
};