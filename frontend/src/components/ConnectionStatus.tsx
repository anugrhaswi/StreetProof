import { useEffect, useState, useCallback } from 'react';
import { Wifi, WifiOff, Loader2 } from 'lucide-react';
import { checkHealth } from '../services/api';

type Status = 'loading' | 'connected' | 'disconnected';

const POLL_INTERVAL_MS = 10000;

export default function ConnectionStatus() {
  const [status, setStatus] = useState<Status>('loading');

  const fetchHealth = useCallback(async () => {
    try {
      await checkHealth();
      setStatus('connected');
    } catch {
      setStatus('disconnected');
    }
  }, []);

  useEffect(() => {
    fetchHealth();
    const interval = setInterval(fetchHealth, POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [fetchHealth]);

  const config = {
    loading: {
      icon: Loader2,
      label: 'Checking connection...',
      className: 'text-gray-400 bg-gray-800/60 border-gray-700',
      iconClass: 'animate-spin',
    },
    connected: {
      icon: Wifi,
      label: 'Backend connected',
      className: 'text-emerald-400 bg-emerald-950/40 border-emerald-800/50',
      iconClass: '',
    },
    disconnected: {
      icon: WifiOff,
      label: 'Backend disconnected',
      className: 'text-red-400 bg-red-950/40 border-red-800/50',
      iconClass: '',
    },
  }[status];

  const Icon = config.icon;

  return (
    <div
      className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full border text-sm font-medium ${config.className}`}
      role="status"
      aria-live="polite"
    >
      <Icon size={16} className={config.iconClass} />
      <span>{config.label}</span>
    </div>
  );
}
