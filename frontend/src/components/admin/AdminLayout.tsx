import { Menu, Shield } from 'lucide-react';
import { useState, type ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAdminAuth } from '../../contexts/AdminAuthContext';
import { useToast } from '../Toast';
import AdminSidebar from './AdminSidebar';

interface AdminLayoutProps {
  title: string;
  children: ReactNode;
}

export default function AdminLayout({ title, children }: AdminLayoutProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const { admin, logout } = useAdminAuth();
  const toast = useToast();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    toast.success('Signed out.');
    navigate('/admin/login', { replace: true });
  };

  return (
    <div className="min-h-screen bg-brand-950 text-gray-100">
      <AdminSidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} onLogout={handleLogout} />

      <div className="lg:pl-64">
        <header className="sticky top-0 z-20 border-b border-gray-800/80 bg-brand-950/90 backdrop-blur-sm">
          <div className="px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <button
                onClick={() => setSidebarOpen(true)}
                className="lg:hidden p-2 -ml-2 text-gray-400 hover:text-white"
                aria-label="Open sidebar"
              >
                <Menu size={20} />
              </button>
              <h1 className="text-lg sm:text-xl font-semibold text-white">{title}</h1>
            </div>
            <div className="flex items-center gap-3 text-sm">
              <div className="hidden sm:flex items-center gap-2 text-gray-400">
                <Shield size={15} className="text-brand-400" />
                <span>{admin?.username ?? 'Admin'}</span>
              </div>
              <button
                onClick={handleLogout}
                className="px-3 py-1.5 rounded-md border border-gray-700 text-gray-300 hover:text-white hover:border-gray-500 transition-colors"
              >
                Logout
              </button>
            </div>
          </div>
        </header>

        <main className="px-4 sm:px-6 lg:px-8 py-6 sm:py-8">{children}</main>
      </div>
    </div>
  );
}
