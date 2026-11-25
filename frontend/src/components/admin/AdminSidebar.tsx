import { Brain, FileText, LayoutDashboard, LogOut, ShieldAlert, X } from 'lucide-react';
import { NavLink } from 'react-router-dom';

interface AdminSidebarProps {
  open: boolean;
  onClose: () => void;
  onLogout: () => void;
}

const navItems = [
  { to: '/admin/dashboard', label: 'Overview', icon: LayoutDashboard, end: true },
  { to: '/admin/reports', label: 'Reports', icon: FileText, end: false },
  { to: '/admin/match-review', label: 'AI Match Review', icon: Brain, end: false },
  { to: '/admin/incidents', label: 'Incidents', icon: ShieldAlert, end: false },
];

function NavItems({ onNavigate, onLogout }: { onNavigate?: () => void; onLogout: () => void }) {
  return (
    <nav className="flex flex-col h-full">
      <div className="px-4 py-5 border-b border-gray-800">
        <p className="text-sm font-semibold text-white">StreetProof Admin</p>
        <p className="text-xs text-gray-500 mt-0.5">Civic intelligence dashboard</p>
      </div>
      <div className="flex-1 px-3 py-4 space-y-1">
        {navItems.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            onClick={onNavigate}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
                isActive
                  ? 'bg-brand-500/15 text-brand-300 border border-brand-500/20'
                  : 'text-gray-400 hover:text-gray-100 hover:bg-gray-800/60 border border-transparent'
              }`
            }
          >
            <Icon size={17} />
            <span>{label}</span>
          </NavLink>
        ))}
      </div>
      <div className="px-3 py-4 border-t border-gray-800">
        <button
          onClick={onLogout}
          className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-gray-400 hover:text-red-300 hover:bg-red-500/10 transition-colors"
        >
          <LogOut size={17} />
          <span>Logout</span>
        </button>
      </div>
    </nav>
  );
}

export default function AdminSidebar({ open, onClose, onLogout }: AdminSidebarProps) {
  return (
    <>
      <aside className="hidden lg:flex lg:w-64 lg:flex-col lg:fixed lg:inset-y-0 bg-gray-950 border-r border-gray-800 z-30">
        <NavItems onLogout={onLogout} />
      </aside>

      {open && (
        <div className="lg:hidden fixed inset-0 z-40">
          <div className="absolute inset-0 bg-black/60" onClick={onClose} aria-hidden="true" />
          <aside className="absolute inset-y-0 left-0 w-72 max-w-[85vw] bg-gray-950 border-r border-gray-800 shadow-2xl">
            <button
              onClick={onClose}
              className="absolute top-4 right-4 text-gray-400 hover:text-white"
              aria-label="Close sidebar"
            >
              <X size={20} />
            </button>
            <NavItems onNavigate={onClose} onLogout={onLogout} />
          </aside>
        </div>
      )}
    </>
  );
}
