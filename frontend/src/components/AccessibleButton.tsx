import React from 'react';

interface AccessibleButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
    ariaLabel?: string;
    ariaDescribedBy?: string;
    children: React.ReactNode;
}

export const AccessibleButton: React.FC<AccessibleButtonProps> = ({
    ariaLabel,
    ariaDescribedBy,
    children,
    ...props
}) => {
    return (
        <button
            aria-label={ariaLabel}
            aria-describedby={ariaDescribedBy}
            {...props}
        >
            {children}
        </button>
    );
};