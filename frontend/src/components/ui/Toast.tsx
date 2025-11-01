import React, { useEffect } from 'react';
import { createPortal } from 'react-dom';

interface ToastProps {
    message: string;
    type: 'success' | 'error' | 'info';
    duration?: number;
    onClose: () => void;
}

export const Toast: React.FC<ToastProps> = ({
    message,
    type,
    duration = 3000,
    onClose
}) => {
    useEffect(() => {
        const timer = setTimeout(onClose, duration);
        return () => clearTimeout(timer);
    }, [duration, onClose]);

    const icon = {
        success: '✓',
        error: '✗',
        info: 'ℹ'
    }[type];

    return createPortal(
        <div className={`toast toast-${type}`} role="alert">
            <span className="toast-icon">{icon}</span>
            <span className="toast-message">{message}</span>
        </div>,
        document.body
    );
};