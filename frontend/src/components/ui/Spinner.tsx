import React from 'react';

type Props = {
  size?: 'sm' | 'md' | 'lg';
  className?: string;
  ariaLabel?: string;
};

const sizeMap: Record<string, string> = {
  sm: 'h-4 w-4',
  md: 'h-6 w-6',
  lg: 'h-8 w-8',
};

const Spinner: React.FC<Props> = ({ size = 'md', className = '', ariaLabel = 'Loading' }) => (
  <svg
    role="status"
    aria-label={ariaLabel}
    className={`animate-spin text-slate-500 ${sizeMap[size]} ${className}`}
    xmlns="http://www.w3.org/2000/svg"
    fill="none"
    viewBox="0 0 24 24"
  >
    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"></path>
  </svg>
);

export default Spinner;
