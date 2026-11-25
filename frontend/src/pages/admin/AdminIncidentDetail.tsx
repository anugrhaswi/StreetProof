import { useCallback, useEffect, useState } from 'react';
import { AlertCircle, ArrowLeft, ExternalLink, Loader2 } from 'lucide-react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import AdminLayout from '../../components/admin/AdminLayout';
import { useAdminAuth } from '../../contexts/AdminAuthContext';
import { ApiError, getAdminIncident, updateAdminIncidentStatus, type Incident } from '../../services/api';

function formatDate(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' });
}

function statusTone(status: string): string {
  if (status === 'open') return 'text-red-300 border-red-500/30 bg-red-500/10';
  if (status === 'closed') return 'text-green-300 border-green-500/30 bg-green-500/10';
  return 'text-gray-300 border-gray-600 bg-gray-500/10';
}

export default function AdminIncidentDetail() {
  const { id } = useParams<{ id: string }>();
  const { logout } = useAdminAuth();
  const navigate = useNavigate();
  const [incident, setIncident] = useState<Incident | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [savingStatus, setSavingStatus] = useState(false);
  const [statusError, setStatusError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const data = await getAdminIncident(id);
      setIncident(data);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        await logout();
        navigate('/admin/login', { replace: true });
        return;
      }
      setError(err instanceof Error ? err.message : 'Failed to load incident.');
    } finally {
      setLoading(false);
    }
  }, [id, logout, navigate]);

  useEffect(() => { void load(); }, [load]);

  const canChangeStatus = incident && incident.status !== 'merged' && !incident.merged_into_incident_id;
  const nextStatus = incident?.status === 'open' ? 'closed' : 'open';

  const handleStatusChange = async () => {
    if (!incident || !canChangeStatus) return;
    const confirmMsg = nextStatus === 'closed'
      ? 'Mark this incident as closed?'
      : 'Reopen this incident?';
    if (!window.confirm(confirmMsg)) return;
    setSavingStatus(true);
    setStatusError(null);
    try {
      const updated = await updateAdminIncidentStatus(incident.id, nextStatus);
      setIncident(updated);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        await logout();
        navigate('/admin/login', { replace: true });
        return;
      }
      setStatusError(err instanceof Error ? err.message : 'Failed to update status.');
    } finally {
      setSavingStatus(false);
    }
  };

  const hasValidCoords = incident && Number.isFinite(incident.latitude) && Number.isFinite(incident.longitude)
    && incident.latitude >= -90 && incident.latitude <= 90 && incident.longitude >= -180 && incident.longitude <= 180;
  const googleMapsUrl = hasValidCoords && incident
    ? `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(incident.latitude)},${encodeURIComponent(incident.longitude)}`
    : null;

  return (
    <AdminLayout title="Incident Detail">
      <div className="space-y-6 max-w-5xl">
        <Link to="/admin/incidents" className="inline-flex items-center gap-1.5 text-sm text-gray-400 hover:text-gray-200">
          <ArrowLeft size={15} /> Back to incidents
        </Link>

        {error && (
          <div className="p-4 rounded-lg border border-red-500/30 bg-red-500/10 text-red-200 text-sm flex items-center gap-2">
            <AlertCircle size={16} /> <span>{error}</span>
          </div>
        )}

        {loading ? (
          <div className="bg-gray-900/50 border border-gray-800 rounded-xl p-8 flex items-center gap-3 text-gray-400"><Loader2 size={18} className="animate-spin" /> Loading incident...</div>
        ) : incident ? (
          <>
            <div className="bg-gray-900/50 border border-gray-800 rounded-xl p-6">
              <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
                <div>
                  <div className="flex flex-wrap items-center gap-2 mb-2">
                    <span className="text-xs px-2.5 py-1 rounded-full border border-gray-700 bg-gray-800 text-gray-300 capitalize">{incident.category}</span>
                    <span className={`text-xs px-2.5 py-1 rounded-full border capitalize ${statusTone(incident.status)}`}>{incident.status}</span>
                  </div>
                  <h2 className="text-xl font-semibold text-white">{incident.title}</h2>
                  <p className="text-sm text-gray-500 mt-1 font-mono">ID: {incident.id}</p>
                </div>
                {canChangeStatus && (
                  <button
                    onClick={() => void handleStatusChange()}
                    disabled={savingStatus}
                    className="px-4 py-2 rounded-lg border border-gray-700 text-sm text-gray-200 hover:border-gray-500 hover:text-white disabled:opacity-50"
                  >
                    {savingStatus ? 'Saving...' : nextStatus === 'closed' ? 'Mark Closed' : 'Reopen Incident'}
                  </button>
                )}
              </div>

              {statusError && <div className="mt-4 text-sm text-red-300">{statusError}</div>}

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-6 text-sm">
                <div><div className="text-gray-500 text-xs uppercase tracking-wide">Created</div><div className="text-gray-300 mt-1">{formatDate(incident.created_at)}</div></div>
                <div><div className="text-gray-500 text-xs uppercase tracking-wide">Updated</div><div className="text-gray-300 mt-1">{formatDate(incident.updated_at)}</div></div>
                <div><div className="text-gray-500 text-xs uppercase tracking-wide">Reports</div><div className="text-gray-300 mt-1">{incident.reports?.length ?? 0}</div></div>
                <div>
                  <div className="text-gray-500 text-xs uppercase tracking-wide">Location</div>
                  {googleMapsUrl ? (
                    <a href={googleMapsUrl} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-brand-400 hover:text-brand-300 mt-1">
                      Open in Google Maps <ExternalLink size={13} />
                    </a>
                  ) : <div className="text-gray-500 mt-1">Location unavailable</div>}
                  <div className="text-xs text-gray-500 mt-0.5">{incident.latitude.toFixed(5)}, {incident.longitude.toFixed(5)}</div>
                </div>
              </div>

              {incident.description && (
                <div className="mt-6 pt-5 border-t border-gray-800">
                  <div className="text-gray-500 text-xs uppercase tracking-wide mb-2">Description</div>
                  <p className="text-gray-300 whitespace-pre-wrap">{incident.description}</p>
                </div>
              )}
            </div>

            <div className="bg-gray-900/50 border border-gray-800 rounded-xl overflow-hidden">
              <div className="px-5 py-4 border-b border-gray-800">
                <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wide">Associated Reports ({incident.reports?.length ?? 0})</h3>
              </div>
              {(incident.reports?.length ?? 0) === 0 ? (
                <div className="p-6 text-sm text-gray-500">No reports associated with this incident.</div>
              ) : (
                <div className="divide-y divide-gray-800/80">
                  {(incident.reports ?? []).map((r) => (
                    <div key={r.id} className="px-5 py-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-gray-200 text-sm font-medium capitalize">{r.category}</span>
                          <span className="text-xs text-gray-500 font-mono">{r.id.slice(0, 8)}…</span>
                        </div>
                        <p className="text-sm text-gray-400 mt-1 line-clamp-2">{r.description}</p>
                        <div className="text-xs text-gray-500 mt-1">{formatDate(r.created_at)}</div>
                      </div>
                      <Link to={`/admin/reports/${r.id}`} className="text-sm text-brand-400 hover:text-brand-300 shrink-0">View Report</Link>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </>
        ) : null}
      </div>
    </AdminLayout>
  );
}
