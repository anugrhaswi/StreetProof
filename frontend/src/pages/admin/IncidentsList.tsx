import { useCallback, useEffect, useState } from 'react';
import { AlertCircle, ChevronLeft, ChevronRight, Eye } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import AdminLayout from '../../components/admin/AdminLayout';
import { useAdminAuth } from '../../contexts/AdminAuthContext';
import { ApiError, getAdminIncidents, type AdminIncidentListItem, type Status } from '../../services/api';

const STATUSES: { value: '' | Status; label: string }[] = [
  { value: '', label: 'All statuses' },
  { value: 'open', label: 'Open' },
  { value: 'closed', label: 'Closed' },
  { value: 'merged', label: 'Merged' },
];

function formatDate(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' });
}

function shortId(id: string): string {
  return id.length > 8 ? `${id.slice(0, 8)}…` : id;
}

function statusTone(status: Status): string {
  if (status === 'open') return 'text-red-300 border-red-500/30 bg-red-500/10';
  if (status === 'closed') return 'text-green-300 border-green-500/30 bg-green-500/10';
  return 'text-gray-300 border-gray-600 bg-gray-500/10';
}

export default function AdminIncidentsList() {
  const { logout } = useAdminAuth();
  const navigate = useNavigate();
  const [items, setItems] = useState<AdminIncidentListItem[]>([]);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [status, setStatusFilter] = useState<'' | Status>('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getAdminIncidents(page, pageSize, status || undefined);
      setItems(data.items);
      setTotal(data.total);
      setTotalPages(data.total_pages);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        await logout();
        navigate('/admin/login', { replace: true });
        return;
      }
      setError(err instanceof Error ? err.message : 'Failed to load incidents.');
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, status, logout, navigate]);

  useEffect(() => { void load(); }, [load]);

  return (
    <AdminLayout title="Incidents">
      <div className="bg-gray-900/50 border border-gray-800 rounded-xl overflow-hidden">
        <div className="p-4 sm:p-5 border-b border-gray-800 flex flex-col sm:flex-row gap-3 sm:items-center sm:justify-between">
          <p className="text-sm text-gray-400">{total} incident{total !== 1 ? 's' : ''}</p>
          <div className="flex gap-3">
            <select
              value={status}
              onChange={(e) => { setPage(1); setStatusFilter(e.target.value as '' | Status); }}
              className="bg-gray-950 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200"
            >
              {STATUSES.map((s) => <option key={s.value || 'all'} value={s.value}>{s.label}</option>)}
            </select>
            <select
              value={pageSize}
              onChange={(e) => { setPage(1); setPageSize(Number(e.target.value)); }}
              className="bg-gray-950 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200"
            >
              {[10, 20, 50, 100].map((n) => <option key={n} value={n}>{n} / page</option>)}
            </select>
          </div>
        </div>

        {error && (
          <div className="m-4 p-4 rounded-lg border border-red-500/30 bg-red-500/10 text-red-200 flex items-center justify-between gap-4 text-sm">
            <div className="flex items-center gap-2"><AlertCircle size={16} /><span>{error}</span></div>
            <button onClick={() => void load()} className="underline hover:no-underline">Retry</button>
          </div>
        )}

        {loading ? (
          <div className="p-5 space-y-3">{Array.from({ length: 5 }).map((_, i) => <div key={i} className="h-14 bg-gray-800/50 rounded-lg animate-pulse" />)}</div>
        ) : items.length === 0 ? (
          <div className="p-10 text-center text-gray-400 text-sm">No incidents found.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-left text-gray-400 bg-gray-900/80">
                <tr>
                  <th className="px-5 py-3 font-medium">Incident</th>
                  <th className="px-5 py-3 font-medium">Category</th>
                  <th className="px-5 py-3 font-medium">Status</th>
                  <th className="px-5 py-3 font-medium">Reports</th>
                  <th className="px-5 py-3 font-medium">Created</th>
                  <th className="px-5 py-3 font-medium">Action</th>
                </tr>
              </thead>
              <tbody>
                {items.map((inc) => (
                  <tr key={inc.id} className="border-t border-gray-800/80">
                    <td className="px-5 py-4">
                      <div className="text-gray-200 font-medium">{inc.title}</div>
                      <div className="text-xs text-gray-500 font-mono mt-0.5">{shortId(inc.id)}</div>
                    </td>
                    <td className="px-5 py-4 text-gray-300 capitalize">{inc.category}</td>
                    <td className="px-5 py-4">
                      <span className={`text-xs px-2 py-1 rounded-full border capitalize ${statusTone(inc.status)}`}>{inc.status}</span>
                    </td>
                    <td className="px-5 py-4 text-gray-300">{inc.report_count}</td>
                    <td className="px-5 py-4 text-gray-400 whitespace-nowrap">{formatDate(inc.created_at)}</td>
                    <td className="px-5 py-4">
                      <Link to={`/admin/incidents/${inc.id}`} className="inline-flex items-center gap-1.5 p-2 rounded-md border border-gray-700 text-gray-300 hover:text-white hover:border-gray-500" aria-label="View incident">
                        <Eye size={15} />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {totalPages > 1 && (
          <div className="flex items-center justify-center gap-4 p-4 border-t border-gray-800 text-sm">
            <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page <= 1} className="inline-flex items-center gap-1 px-3 py-1.5 rounded border border-gray-700 text-gray-300 disabled:opacity-40"><ChevronLeft size={16} /> Prev</button>
            <span className="text-gray-400">Page {page} of {totalPages}</span>
            <button onClick={() => setPage((p) => Math.min(totalPages, p + 1))} disabled={page >= totalPages} className="inline-flex items-center gap-1 px-3 py-1.5 rounded border border-gray-700 text-gray-300 disabled:opacity-40">Next <ChevronRight size={16} /></button>
          </div>
        )}
      </div>
    </AdminLayout>
  );
}
