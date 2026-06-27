import React from "react";
import { useAuth } from "../../context/AuthContext";
import { canAccess } from "../../lib/permissions";
import type { UserRole } from "../../types";

interface CanProps {
  roles: UserRole[];
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

/**
 * Procedural UI component for granular role-based rendering.
 */
export const Can: React.FC<CanProps> = ({
  roles,
  children,
  fallback = null,
}) => {
  const { user } = useAuth();

  if (!user || !canAccess(user.role, roles)) {
    return <>{fallback}</>;
  }

  return <>{children}</>;
};

export const usePermission = () => {
  const { user } = useAuth();

  return {
    can: (roles: UserRole[]) => !!user && canAccess(user.role, roles),
    role: user?.role as UserRole | undefined,
  };
};
