import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react';
import { X, CheckCircle, AlertCircle, AlertTriangle } from 'lucide-react';

type ToastType = 'success' | 'error' | 'warning';

interface ToastItem {
  id: string;
  type: ToastType;
  message: string;
}

interface ToastContextValue {
  success: (message: string) => void;
  error: (message: string) => void;
  warning: (message: string) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

function ToastIcon({ type }: { type: ToastType }) {
  if (type === 'success') return <CheckCircle size={18} className="text-emerald-400" />;
  if (type === 'error') return <AlertCircle size={18} className="text-red-400" />;
  return <AlertTriangle size={18} className="text-amber-400" />;
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const remove = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const push = useCallback((type: ToastType, message: string) => {
    const id = `${Date.now()}-${Math.random().toString(36).slice(2)}`;
    setToasts((prev) => [...prev, { id, type, message }]);
    window.setTimeout(() => remove(id), 5000);
  }, [remove]);

  const value = useMemo<ToastContextValue>(() => ({
    success: (m) => push('success', m),
    error: (m) => push('error', m),
    warning: (m) => push('warning', m),
  }), [push]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div
        className="fixed top-4 right-4 z-50 flex flex-col gap-2 w-[min(360px,calc(100vw-2rem))]"
        aria-live="polite"
        aria-atomic="false"
      >
        {toasts.map((t) => (
          <div
            key={t.id}
            role="alert"
            className="flex items-start gap-3 p-3 rounded-lg border border-gray-700 bg-gray-900/95 backdrop-blur shadow-lg text-sm text-gray-100"
          >
            <ToastIcon type={t.type} />
            <p className="flex-1 leading-relaxed">{t.message}</p>
            <button
              onClick={() => remove(t.id)}
              className="text-gray-400 hover:text-white transition-colors"
              aria-label="Dismiss notification"
            >
              <X size={16} />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToast must be used within ToastProvider');
  return ctx;
}
