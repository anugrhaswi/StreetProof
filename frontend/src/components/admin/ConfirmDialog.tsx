import { AlertTriangle, X } from 'lucide-react';

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  loading?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export default function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel = 'Delete',
  loading = false,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/60" onClick={loading ? undefined : onCancel} aria-hidden="true" />
      <div className="relative w-full max-w-md bg-gray-950 border border-gray-800 rounded-xl shadow-2xl p-6">
        <button
          onClick={onCancel}
          disabled={loading}
          className="absolute top-4 right-4 text-gray-400 hover:text-white disabled:opacity-40"
          aria-label="Close"
        >
          <X size={18} />
        </button>
        <div className="flex items-start gap-3 mb-4">
          <div className="p-2 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400">
            <AlertTriangle size={18} />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-white">{title}</h3>
            <p className="text-sm text-gray-400 mt-1">{message}</p>
          </div>
        </div>
        <div className="flex justify-end gap-3 mt-6">
          <button
            onClick={onCancel}
            disabled={loading}
            className="px-4 py-2 rounded-lg border border-gray-700 text-gray-300 hover:text-white hover:border-gray-500 disabled:opacity-50 text-sm"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            disabled={loading}
            className="px-4 py-2 rounded-lg bg-red-600 hover:bg-red-500 text-white disabled:opacity-50 text-sm font-medium"
          >
            {loading ? 'Deleting...' : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
