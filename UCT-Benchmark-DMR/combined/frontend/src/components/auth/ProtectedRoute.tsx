import { Navigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '@/stores/authStore';

const AUTH_ENABLED = import.meta.env.VITE_AUTH_ENABLED === 'true';

interface ProtectedRouteProps {
  children: React.ReactNode;
}

/**
 * Route guard that redirects unauthenticated users to /login.
 *
 * When VITE_AUTH_ENABLED is not "true", the guard is a no-op and renders
 * children unconditionally so the app works without authentication.
 */
export function ProtectedRoute({ children }: ProtectedRouteProps) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const location = useLocation();

  if (AUTH_ENABLED && !isAuthenticated) {
    // Preserve the intended destination so we can redirect back after login
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <>{children}</>;
}
