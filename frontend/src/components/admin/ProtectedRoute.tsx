import { Navigate, useLocation } from 'react-router-dom';
import type { ReactNode } from 'react';
import { useAdminAuth } from '../../contexts/AdminAuthContext';

export default function ProtectedRoute({ children }: { children: ReactNode }) {
  const { admin, isLoading } = useAdminAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="min-h-[50vh] flex items-center justify-center text-gray-400 text-sm">
        Checking admin session...
      </div>
    );
  }

  if (!admin?.authenticated) {
    return <Navigate to="/admin/login" replace state={{ from: location.pathname }} />;
  }

  return <>{children}</>;
}
