import React from 'react';
import './LoadingSpinner.css';

interface LoadingSpinnerProps {
    size?: 'small' | 'medium' | 'large';
    message?: string;
    fullScreen?: boolean;
}

export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({
    size = 'medium',
    message,
    fullScreen = false
}) => {
    const sizeClasses = {
        small: 'spinner-small',
        medium: 'spinner-medium',
        large: 'spinner-large'
    };

    const content = (
        <div className={`loading-spinner ${fullScreen ? 'fullscreen' : ''}`}>
            <div className={`spinner ${sizeClasses[size]}`} />
            {message && <p className="loading-message">{message}</p>}
        </div>
    );

    return content;
};