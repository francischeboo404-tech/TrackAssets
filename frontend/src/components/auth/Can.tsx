import React from 'react';
import { useAuth } from '../../context/AuthContext';
import type { UserRole } from '../../types';

interface CanProps {
  roles: UserRole[];
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

/**
 * Procedural UI component for granular role-based rendering.
 */
export const Can: React.FC<CanProps> = ({ roles, children, fallback = null }) => {
  const { user } = useAuth();

  if (!user || (user.role !== 'admin' && !roles.includes(user.role as UserRole))) {
    return <>{fallback}</>;
  }

  return <>{children}</>;
};

export const usePermission = () => {
  const { user } = useAuth();
  
  return {
    can: (roles: UserRole[]) => user && (user.role === 'admin' || roles.includes(user.role as UserRole)),
    role: user?.role as UserRole | undefined
  };
};
