/** Route guard – redirects unauthenticated users to login, unauthorized to dashboard. */

import { Navigate } from "react-router-dom";
import type { ReactNode } from "react";

import { useAuth } from "../hooks/useAuth";
import { type AppFeature, usePermissions } from "../hooks/usePermissions";
import { HOME_ROUTE, LOGIN_ROUTE } from "../lib/routes";

interface ProtectedRouteProps {
  children: ReactNode;
  requiredFeature?: AppFeature;
  requiredWrite?: boolean;
}

export function ProtectedRoute({ children, requiredFeature, requiredWrite = false }: ProtectedRouteProps) {
  const { isAuthenticated, isAuthLoading } = useAuth();
  const { canAccess, canWrite } = usePermissions();

  if (isAuthLoading) {
    return null; // Wait for auto-login or initial token check
  }

  if (!isAuthenticated) {
    return <Navigate to={LOGIN_ROUTE} replace />;
  }

  if (requiredFeature && !canAccess(requiredFeature)) {
    return <Navigate to={HOME_ROUTE} replace />;
  }

  if (requiredFeature && requiredWrite && !canWrite(requiredFeature)) {
    return <Navigate to={HOME_ROUTE} replace />;
  }

  return <>{children}</>;
}
