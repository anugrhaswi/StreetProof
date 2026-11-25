import { Plus } from 'lucide-react';
import { Link, NavLink, useLocation } from 'react-router-dom';
import type { ReactNode } from 'react';

interface LayoutProps {
  children: ReactNode;
}

const linkClass = ({ isActive }: { isActive: boolean }) =>
  `text-sm hover:text-white transition-colors ${isActive ? 'text-white' : 'text-gray-400'}`;

export default function Layout({ children }: LayoutProps) {
  const location = useLocation();
  const isHome = location.pathname === '/';

  return (
    <div className={`bg-brand-950 text-gray-100 flex flex-col ${isHome ? 'h-screen overflow-hidden' : 'min-h-screen'}`}>
      <header className="border-b border-white/10 bg-[#1a1a1a]/95 backdrop-blur-sm sticky top-0 z-30">
        <nav className="max-w-7xl mx-auto px-4 sm:px-6 h-[64px] sm:h-[72px] flex items-center justify-between gap-4">
          <Link to="/" className="flex items-center gap-3 shrink-0 min-w-0" aria-label="StreetProof home">
            <img
              src="/brand/logo.jpeg"
              alt="StreetProof logo"
              className="h-11 w-11 sm:h-14 sm:w-14 object-contain shrink-0"
              draggable={false}
            />
            <span className="text-lg sm:text-xl font-semibold tracking-tight text-white truncate">StreetProof</span>
          </Link>

          <div className="flex items-center gap-3 sm:gap-5">
            <div className="hidden sm:flex items-center gap-5">
              <NavLink to="/reports" className={linkClass}>Reports</NavLink>
            </div>
            <Link
              to="/report"
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg bg-brand-500 hover:bg-brand-400 text-white text-sm font-medium transition-colors shrink-0"
            >
              <Plus size={15} />
              <span>Report Issue</span>
            </Link>
          </div>
        </nav>
      </header>

      <main className={isHome ? 'flex-1 min-h-0' : 'flex-1'}>{children}</main>

      {!isHome && (
        <footer className="border-t border-gray-800/60 py-6 text-center text-sm text-gray-500">
          StreetProof &mdash; Civic infrastructure issue intelligence
        </footer>
      )}
    </div>
  );
}
