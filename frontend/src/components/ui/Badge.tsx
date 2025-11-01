import React from 'react';
import './Badge.css';

interface BadgeProps {
    children: React.ReactNode;
    variant?: 'primary' | 'success' | 'warning' | 'danger' | 'info' | 'default';
    size?: 'small' | 'medium' | 'large';
    className?: string;
}

export const Badge: React.FC<BadgeProps> = ({
    children,
    variant = 'default',
    size = 'medium',
    className = ''
}) => {
    const classes = [
        'badge',
        `badge-${variant}`,
        `badge-${size}`,
        className
    ].filter(Boolean).join(' ');

    return (
        <span className={classes}>
            {children}
        </span>
    );
};

// Status-specific badges
export const StatusBadge: React.FC<{ status: string }> = ({ status }) => {
    const variantMap: Record<string, BadgeProps['variant']> = {
        success: 'success',
        failed: 'danger',
        running: 'info',
        pending: 'warning',
        cancelled: 'default',
        active: 'success',
        draft: 'default',
        deprecated: 'warning'
    };

    return (
        <Badge variant={variantMap[status] || 'default'}>
            {status}
        </Badge>
    );
};