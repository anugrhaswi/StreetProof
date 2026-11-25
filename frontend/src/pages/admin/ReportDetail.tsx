import { useCallback, useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { AlertCircle, ArrowLeft, Calendar, MapPin, Trash2 } from 'lucide-react';
import AdminLayout from '../../components/admin/AdminLayout';
import ConfirmDialog from '../../components/admin/ConfirmDialog';
import { useAdminAuth } from '../../contexts/AdminAuthContext';
import { useToast } from '../../components/Toast';
import { ApiError, deleteAdminReport, getAdminReport, imageUrl, type AdminReportDetail } from '../../services/api';

function formatDate(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' });
}

export default function AdminReportDetailPage() {
  const { reportId } = useParams<{ reportId: string }>();
  const { logout } = useAdminAuth();
  const navigate = useNavigate();
  const toast = useToast();
  const [report, setReport] = useState<AdminReportDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const load = useCallback(async () => {
    if (!reportId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await getAdminReport(reportId);
      setReport(data);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) { await logout(); navigate('/admin/login', { replace: true }); return; }
      setError(err instanceof Error ? err.message : 'Failed to load report.');
    } finally {
      setLoading(false);
    }
  }, [reportId, logout, navigate]);

  useEffect(() => { void load(); }, [load]);

  const onDelete = async () => {
    if (!reportId) return;
    setDeleting(true);
    try {
      await deleteAdminReport(reportId);
      toast.success('Report deleted.');
      navigate('/admin/reports', { replace: true });
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) { await logout(); navigate('/admin/login', { replace: true }); return; }
      toast.error(err instanceof Error ? err.message : 'Failed to delete report.');
    } finally {
      setDeleting(false);
      setConfirmOpen(false);
    }
  };

  return (
    <AdminLayout title="Report Detail">
      <div className="mb-4">
        <Link to="/admin/reports" className="inline-flex items-center gap-2 text-sm text-gray-400 hover:text-white"><ArrowLeft size={15} /> Back to reports</Link>
      </div>

      {error && (
        <div className="mb-6 p-4 rounded-lg border border-red-500/30 bg-red-500/10 text-red-200 flex items-center justify-between gap-4 text-sm">
          <div className="flex items-center gap-2"><AlertCircle size={16} /><span>{error}</span></div>
          <button onClick={() => void load()} className="underline hover:no-underline">Retry</button>
        </div>
      )}

      {loading ? (
        <div className="space-y-4">{Array.from({ length: 4 }).map((_, i) => <div key={i} className="h-28 bg-gray-900/40 border border-gray-800 rounded-xl animate-pulse" />)}</div>
      ) : report ? (
        <div className="space-y-6">
          <div className="bg-gray-900/50 border border-gray-800 rounded-xl p-5 sm:p-6">
            <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4 mb-5">
              <div>
                <div className="flex flex-wrap items-center gap-2 mb-2">
                  <span className="text-xs px-2 py-1 rounded-full bg-brand-500/10 text-brand-300 border border-brand-500/20 capitalize">{report.category}</span>
                  <span className="text-xs px-2 py-1 rounded-full border border-gray-700 text-gray-300 capitalize">{report.incident_status ?? 'Unknown'}</span>
                </div>
                <p className="text-xs text-gray-500 font-mono">Report ID: {report.id}</p>
              </div>
              <button onClick={() => setConfirmOpen(true)} className="inline-flex items-center gap-2 px-3 py-2 rounded-lg border border-red-500/30 text-red-300 hover:bg-red-500/10 text-sm">
                <Trash2 size={15} /> Delete report
              </button>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="lg:col-span-1">
                {report.image_path ? (
                  <img src={imageUrl(report.image_path)} alt="Report" className="w-full rounded-lg border border-gray-800 object-cover max-h-80 bg-gray-950" />
                ) : (
                  <div className="w-full h-56 rounded-lg border border-gray-800 bg-gray-950 flex items-center justify-center text-gray-500 text-sm">No image</div>
                )}
              </div>
              <div className="lg:col-span-2 space-y-4">
                <div>
                  <h2 className="text-sm text-gray-400 mb-1">Description</h2>
                  <p className="text-gray-200 whitespace-pre-wrap">{report.description}</p>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
                  <div><p className="text-gray-500">Submitted</p><p className="text-gray-200 flex items-center gap-2"><Calendar size={14} /> {formatDate(report.created_at)}</p></div>
                  <div><p className="text-gray-500">Coordinates</p><p className="text-gray-200 flex items-center gap-2"><MapPin size={14} /> {report.latitude.toFixed(5)}, {report.longitude.toFixed(5)}</p></div>
                  <div><p className="text-gray-500">Incident ID</p><p className="text-gray-200 font-mono text-xs break-all">{report.incident_id}</p></div>
                  <div><p className="text-gray-500">Matching Job</p><p className="text-gray-200 capitalize">{report.matching_job?.status ?? 'None'}</p></div>
                  <div><p className="text-gray-500">SHA-256</p><p className="text-gray-200 font-mono text-xs break-all">{report.sha256_hash ?? '—'}</p></div>
                  <div><p className="text-gray-500">pHash</p><p className="text-gray-200 font-mono text-xs break-all">{report.phash}</p></div>
                </div>
              </div>
            </div>
          </div>

          {report.incident && (
            <div className="bg-gray-900/50 border border-gray-800 rounded-xl p-5">
              <h3 className="text-sm font-medium text-white mb-3">Associated Incident</h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
                <div><p className="text-gray-500">Title</p><p className="text-gray-200">{report.incident.title}</p></div>
                <div><p className="text-gray-500">Status</p><p className="text-gray-200 capitalize">{report.incident.status}</p></div>
                <div><p className="text-gray-500">Category</p><p className="text-gray-200 capitalize">{report.incident.category}</p></div>
                <div><p className="text-gray-500">Incident ID</p><p className="text-gray-200 font-mono text-xs break-all">{report.incident.id}</p></div>
              </div>
            </div>
          )}

          <div className="bg-gray-900/50 border border-gray-800 rounded-xl p-5">
            <h3 className="text-sm font-medium text-white mb-3">Match Suggestions ({report.match_suggestions.length})</h3>
            {report.match_suggestions.length === 0 ? (
              <p className="text-sm text-gray-400">No match suggestions for this report.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="text-left text-gray-400">
                    <tr><th className="py-2 pr-4 font-medium">Incident</th><th className="py-2 pr-4 font-medium">Similarity</th><th className="py-2 pr-4 font-medium">Status</th><th className="py-2 font-medium">Matched Report</th></tr>
                  </thead>
                  <tbody>
                    {report.match_suggestions.map((s) => (
                      <tr key={s.id} className="border-t border-gray-800">
                        <td className="py-2 pr-4 text-gray-300">{s.incident_title ?? s.incident_id}</td>
                        <td className="py-2 pr-4 text-gray-300">{(s.similarity_score * 100).toFixed(1)}%</td>
                        <td className="py-2 pr-4 text-gray-300 capitalize">{s.status}</td>
                        <td className="py-2 text-gray-400 font-mono text-xs">{s.matched_report_id}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      ) : null}

      <ConfirmDialog
        open={confirmOpen}
        title="Delete report?"
        message="This will permanently delete this report and its associated matching data. This action cannot be undone."
        confirmLabel="Delete report"
        loading={deleting}
        onConfirm={() => void onDelete()}
        onCancel={() => { if (!deleting) setConfirmOpen(false); }}
      />
    </AdminLayout>
  );
}
