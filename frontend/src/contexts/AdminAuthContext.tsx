import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { adminLogin, adminLogout, getAdminSession, type AdminSession } from '../services/api';

interface AdminAuthContextValue {
  admin: AdminSession | null;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
}

const AdminAuthContext = createContext<AdminAuthContextValue | null>(null);

export function AdminAuthProvider({ children }: { children: ReactNode }) {
  const [admin, setAdmin] = useState<AdminSession | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const session = await getAdminSession();
      setAdmin(session);
    } catch {
      setAdmin({ authenticated: false, username: null });
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const login = useCallback(async (username: string, password: string) => {
    const res = await adminLogin(username, password);
    setAdmin({ authenticated: res.authenticated, username: res.username });
  }, []);

  const logout = useCallback(async () => {
    try {
      await adminLogout();
    } finally {
      setAdmin({ authenticated: false, username: null });
    }
  }, []);

  const value = useMemo(() => ({ admin, isLoading, login, logout, refresh }), [admin, isLoading, login, logout, refresh]);

  return <AdminAuthContext.Provider value={value}>{children}</AdminAuthContext.Provider>;
}

export function useAdminAuth(): AdminAuthContextValue {
  const ctx = useContext(AdminAuthContext);
  if (!ctx) throw new Error('useAdminAuth must be used within AdminAuthProvider');
  return ctx;
}
