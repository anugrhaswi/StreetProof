import { useCallback, useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { AlertCircle, ChevronLeft, ChevronRight, Eye, Search, Trash2 } from 'lucide-react';
import AdminLayout from '../../components/admin/AdminLayout';
import ConfirmDialog from '../../components/admin/ConfirmDialog';
import { useAdminAuth } from '../../contexts/AdminAuthContext';
import { useToast } from '../../components/Toast';
import {
  ApiError,
  deleteAdminReport,
  getAdminReports,
  imageUrl,
  type AdminReportListItem,
  type Category,
  type Status,
} from '../../services/api';

const CATEGORIES: { value: '' | Category; label: string }[] = [
  { value: '', label: 'All categories' },
  { value: 'pothole', label: 'Pothole' },
  { value: 'streetlight', label: 'Streetlight' },
  { value: 'garbage', label: 'Garbage' },
  { value: 'graffiti', label: 'Graffiti' },
  { value: 'sidewalk', label: 'Sidewalk' },
  { value: 'signage', label: 'Signage' },
  { value: 'drainage', label: 'Drainage' },
  { value: 'other', label: 'Other' },
];

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
function shortId(id: string): string { return id.length > 8 ? `${id.slice(0, 8)}…` : id; }

export default function AdminReportsList() {
  const { logout } = useAdminAuth();
  const navigate = useNavigate();
  const toast = useToast();

  const [items, setItems] = useState<AdminReportListItem[]>([]);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [search, setSearch] = useState('');
  const [searchInput, setSearchInput] = useState('');
  const [category, setCategory] = useState<'' | Category>('');
  const [status, setStatus] = useState<'' | Status>('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<AdminReportListItem | null>(null);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    const t = window.setTimeout(() => { setPage(1); setSearch(searchInput.trim()); }, 300);
    return () => window.clearTimeout(t);
  }, [searchInput]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getAdminReports({
        page, page_size: pageSize,
        search: search || undefined,
        category: category || undefined,
        status: status || undefined,
      });
      setItems(data.items);
      setTotal(data.total);
      setTotalPages(data.total_pages);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        await logout();
        navigate('/admin/login', { replace: true });
        return;
      }
      setError(err instanceof Error ? err.message : 'Failed to load reports.');
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, search, category, status, logout, navigate]);

  useEffect(() => { void load(); }, [load]);

  const onDelete = async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await deleteAdminReport(deleteTarget.id);
      toast.success('Report deleted.');
      setDeleteTarget(null);
      // Refresh; if last item on page, step back.
      const isLastOnPage = items.length === 1 && page > 1;
      if (isLastOnPage) setPage((p) => p - 1);
      else await load();
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        await logout(); navigate('/admin/login', { replace: true }); return;
      }
      toast.error(err instanceof Error ? err.message : 'Failed to delete report.');
    } finally {
      setDeleting(false);
    }
  };

  return (
    <AdminLayout title="Reports">
      <div className="bg-gray-900/50 border border-gray-800 rounded-xl overflow-hidden">
        <div className="p-4 sm:p-5 border-b border-gray-800 space-y-4">
          <div className="flex flex-col sm:flex-row gap-3 sm:items-center sm:justify-between">
            <p className="text-sm text-gray-400">{total} report{total !== 1 ? 's' : ''}</p>
            <div className="relative w-full sm:w-72">
              <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
              <input
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                placeholder="Search ID or description..."
                className="w-full pl-9 pr-3 py-2 rounded-lg bg-gray-950 border border-gray-700 text-sm text-gray-100 focus:outline-none focus:ring-2 focus:ring-brand-500/40"
              />
            </div>
          </div>
          <div className="flex flex-col sm:flex-row gap-3">
            <select value={category} onChange={(e) => { setPage(1); setCategory(e.target.value as '' | Category); }} className="bg-gray-950 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200">
              {CATEGORIES.map((c) => <option key={c.value || 'all'} value={c.value}>{c.label}</option>)}
            </select>
            <select value={status} onChange={(e) => { setPage(1); setStatus(e.target.value as '' | Status); }} className="bg-gray-950 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200">
              {STATUSES.map((s) => <option key={s.value || 'all'} value={s.value}>{s.label}</option>)}
            </select>
            <select value={pageSize} onChange={(e) => { setPage(1); setPageSize(Number(e.target.value)); }} className="bg-gray-950 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 sm:ml-auto">
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
          <div className="p-5 space-y-3">{Array.from({ length: 5 }).map((_, i) => <div key={i} className="h-16 bg-gray-800/50 rounded-lg animate-pulse" />)}</div>
        ) : items.length === 0 ? (
          <div className="p-10 text-center text-gray-400 text-sm">No reports found.</div>
        ) : (
          <>
            <div className="hidden md:block overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="text-left text-gray-400 bg-gray-900/80">
                  <tr>
                    <th className="px-5 py-3 font-medium">Report</th>
                    <th className="px-5 py-3 font-medium">Category</th>
                    <th className="px-5 py-3 font-medium">Description</th>
                    <th className="px-5 py-3 font-medium">Submitted</th>
                    <th className="px-5 py-3 font-medium">Incident</th>
                    <th className="px-5 py-3 font-medium">Status</th>
                    <th className="px-5 py-3 font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((r) => (
                    <tr key={r.id} className="border-t border-gray-800/80 align-top">
                      <td className="px-5 py-4">
                        <div className="flex items-center gap-3">
                          {r.image_path ? <img src={imageUrl(r.image_path)} alt="" className="w-10 h-10 rounded-md object-cover border border-gray-700 bg-gray-800" /> : <div className="w-10 h-10 rounded-md border border-gray-700 bg-gray-800" />}
                          <span className="text-gray-300 font-mono text-xs">{shortId(r.id)}</span>
                        </div>
                      </td>
                      <td className="px-5 py-4 text-gray-300 capitalize">{r.category}</td>
                      <td className="px-5 py-4 text-gray-400 max-w-[240px]"><p className="line-clamp-2">{r.description}</p></td>
                      <td className="px-5 py-4 text-gray-400 whitespace-nowrap">{formatDate(r.created_at)}</td>
                      <td className="px-5 py-4 text-gray-400 font-mono text-xs">{shortId(r.incident_id)}</td>
                      <td className="px-5 py-4"><span className="text-xs px-2 py-1 rounded-full border border-gray-700 text-gray-300 capitalize">{r.incident_status ?? '—'}</span></td>
                      <td className="px-5 py-4">
                        <div className="flex items-center gap-2">
                          <Link to={`/admin/reports/${r.id}`} className="p-2 rounded-md border border-gray-700 text-gray-300 hover:text-white hover:border-gray-500" aria-label="View report"><Eye size={15} /></Link>
                          <button onClick={() => setDeleteTarget(r)} className="p-2 rounded-md border border-red-500/30 text-red-300 hover:bg-red-500/10" aria-label="Delete report"><Trash2 size={15} /></button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="md:hidden p-4 space-y-3">
              {items.map((r) => (
                <div key={r.id} className="bg-gray-950/40 border border-gray-800 rounded-lg p-4">
                  <div className="flex gap-3">
                    {r.image_path ? <img src={imageUrl(r.image_path)} alt="" className="w-14 h-14 rounded-md object-cover border border-gray-700 bg-gray-800" /> : <div className="w-14 h-14 rounded-md border border-gray-700 bg-gray-800" />}
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2 mb-1"><span className="text-xs px-2 py-0.5 rounded-full bg-brand-500/10 text-brand-300 border border-brand-500/20 capitalize">{r.category}</span><span className="text-xs text-gray-500 capitalize">{r.incident_status ?? '—'}</span></div>
                      <p className="text-sm text-gray-300 line-clamp-2">{r.description}</p>
                      <p className="text-xs text-gray-500 mt-1">{formatDate(r.created_at)}</p>
                      <p className="text-xs text-gray-500 font-mono mt-0.5">ID {shortId(r.id)}</p>
                    </div>
                  </div>
                  <div className="flex gap-2 mt-3">
                    <Link to={`/admin/reports/${r.id}`} className="flex-1 text-center px-3 py-2 rounded-md border border-gray-700 text-gray-300 text-sm hover:text-white">View</Link>
                    <button onClick={() => setDeleteTarget(r)} className="flex-1 px-3 py-2 rounded-md border border-red-500/30 text-red-300 text-sm hover:bg-red-500/10">Delete</button>
                  </div>
                </div>
              ))}
            </div>
          </>
        )}

        {totalPages > 1 && (
          <div className="flex items-center justify-center gap-4 p-4 border-t border-gray-800 text-sm">
            <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page <= 1} className="inline-flex items-center gap-1 px-3 py-1.5 rounded border border-gray-700 text-gray-300 disabled:opacity-40"><ChevronLeft size={16} /> Prev</button>
            <span className="text-gray-400">Page {page} of {totalPages}</span>
            <button onClick={() => setPage((p) => Math.min(totalPages, p + 1))} disabled={page >= totalPages} className="inline-flex items-center gap-1 px-3 py-1.5 rounded border border-gray-700 text-gray-300 disabled:opacity-40">Next <ChevronRight size={16} /></button>
          </div>
        )}
      </div>

      <ConfirmDialog
        open={!!deleteTarget}
        title="Delete report?"
        message={deleteTarget ? `This will permanently delete report ${shortId(deleteTarget.id)} and its associated matching data. This action cannot be undone.` : ''}
        confirmLabel="Delete report"
        loading={deleting}
        onConfirm={() => void onDelete()}
        onCancel={() => { if (!deleting) setDeleteTarget(null); }}
      />
    </AdminLayout>
  );
}
