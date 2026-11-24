import { Shield } from 'lucide-react';
import type { ReactNode } from 'react';

interface LayoutProps {
  children: ReactNode;
}

export default function Layout({ children }: LayoutProps) {
  return (
    <div className="min-h-screen bg-brand-950 text-gray-100 flex flex-col">
      <header className="border-b border-gray-800/80 bg-brand-950/80 backdrop-blur-sm sticky top-0 z-10">
        <nav className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="p-1.5 rounded-lg bg-brand-500/10 border border-brand-500/20">
              <Shield size={20} className="text-brand-400" />
            </div>
            <span className="text-lg font-semibold tracking-tight text-white">StreetProof</span>
          </div>
          <div className="flex items-center gap-6 text-sm text-gray-400">
            <span className="hover:text-gray-200 transition-colors cursor-default">Report</span>
            <span className="hover:text-gray-200 transition-colors cursor-default">Map</span>
            <span className="hover:text-gray-200 transition-colors cursor-default">Dashboard</span>
          </div>
        </nav>
      </header>

      <main className="flex-1">{children}</main>

      <footer className="border-t border-gray-800/60 py-6 text-center text-sm text-gray-500">
        StreetProof &mdash; Civic infrastructure issue intelligence
      </footer>
    </div>
  );
}
