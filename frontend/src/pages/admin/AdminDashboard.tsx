import { AlertCircle, Calendar, CheckCircle2, Clock, FileText, GitMerge, Loader2, MapPin, XCircle } from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import AdminLayout from '../../components/admin/AdminLayout';
import { useAdminAuth } from '../../contexts/AdminAuthContext';
import {
  ApiError,
  getDashboardStats,
  getRecentReports,
  imageUrl,
  type DashboardStats,
  type RecentReport,
} from '../../services/api';

function formatDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' });
}

function shortId(id: string): string {
  return id.length > 8 ? `${id.slice(0, 8)}…` : id;
}

function StatCard({
  label,
  value,
  icon: Icon,
  tone,
}: {
  label: string;
  value: number;
  icon: typeof FileText;
  tone: string;
}) {
  return (
    <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-5">
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm text-gray-400">{label}</p>
        <div className={`p-2 rounded-lg border ${tone}`}>
          <Icon size={17} />
        </div>
      </div>
      <p className="mt-3 text-3xl font-semibold text-white">{value}</p>
    </div>
  );
}

export default function AdminDashboard() {
  const { logout } = useAdminAuth();
  const navigate = useNavigate();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [recent, setRecent] = useState<RecentReport[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [statsRes, recentRes] = await Promise.all([getDashboardStats(), getRecentReports()]);
      setStats(statsRes);
      setRecent(recentRes);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        await logout();
        navigate('/admin/login', { replace: true });
        return;
      }
      setError(err instanceof Error ? err.message : 'Failed to load dashboard data.');
    } finally {
      setLoading(false);
    }
  }, [logout, navigate]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <AdminLayout title="Overview">
      {error && (
        <div className="mb-6 p-4 rounded-lg border border-red-500/30 bg-red-500/10 text-red-200 flex items-center justify-between gap-4">
          <div className="flex items-center gap-2 text-sm">
            <AlertCircle size={16} />
            <span>{error}</span>
          </div>
          <button onClick={() => void load()} className="text-sm underline hover:no-underline">Retry</button>
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4 mb-8">
        {loading || !stats ? (
          Array.from({ length: 10 }).map((_, i) => (
            <div key={i} className="h-[116px] bg-gray-900/40 border border-gray-800 rounded-xl animate-pulse" />
          ))
        ) : (
          <>
            <StatCard label="Total Reports" value={stats.total_reports} icon={FileText} tone="text-blue-300 bg-blue-500/10 border-blue-500/20" />
            <StatCard label="Reports (7 Days)" value={stats.reports_last_7_days} icon={Calendar} tone="text-violet-300 bg-violet-500/10 border-violet-500/20" />
            <StatCard label="Open Incidents" value={stats.open_incidents} icon={MapPin} tone="text-red-300 bg-red-500/10 border-red-500/20" />
            <StatCard label="Closed Incidents" value={stats.closed_incidents} icon={CheckCircle2} tone="text-emerald-300 bg-emerald-500/10 border-emerald-500/20" />
            <StatCard label="Merged Incidents" value={stats.merged_incidents} icon={GitMerge} tone="text-gray-300 bg-gray-500/10 border-gray-500/20" />
            <StatCard label="Total Incidents" value={stats.total_incidents} icon={MapPin} tone="text-sky-300 bg-sky-500/10 border-sky-500/20" />
            <StatCard label="Pending Suggestions" value={stats.pending_suggestions} icon={Clock} tone="text-amber-300 bg-amber-500/10 border-amber-500/20" />
            <StatCard label="Pending Jobs" value={stats.pending_jobs} icon={Loader2} tone="text-orange-300 bg-orange-500/10 border-orange-500/20" />
            <StatCard label="Completed Jobs" value={stats.completed_jobs} icon={CheckCircle2} tone="text-teal-300 bg-teal-500/10 border-teal-500/20" />
            <StatCard label="Failed Jobs" value={stats.failed_jobs} icon={XCircle} tone="text-red-300 bg-red-500/10 border-red-500/20" />
          </>
        )}
      </div>

      <section className="bg-gray-900/50 border border-gray-800 rounded-xl overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-800 flex items-center justify-between">
          <h2 className="text-base font-medium text-white">Recent Reports</h2>
          <span className="text-xs text-gray-500">Latest 5 submissions</span>
        </div>

        {loading ? (
          <div className="p-5 space-y-3">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="h-14 bg-gray-800/50 rounded-lg animate-pulse" />
            ))}
          </div>
        ) : !recent || recent.length === 0 ? (
          <div className="p-8 text-center text-gray-400 text-sm">No reports submitted yet.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-left text-gray-400 bg-gray-900/80">
                <tr>
                  <th className="px-5 py-3 font-medium">Report</th>
                  <th className="px-5 py-3 font-medium">Category</th>
                  <th className="px-5 py-3 font-medium">Description</th>
                  <th className="px-5 py-3 font-medium">Submitted</th>
                  <th className="px-5 py-3 font-medium">Incident</th>
                  <th className="px-5 py-3 font-medium">Link</th>
                </tr>
              </thead>
              <tbody>
                {recent.map((r) => (
                  <tr key={r.id} className="border-t border-gray-800/80 align-top">
                    <td className="px-5 py-4">
                      <div className="flex items-center gap-3">
                        {r.image_path ? (
                          <img
                            src={imageUrl(r.image_path)}
                            alt=""
                            className="w-10 h-10 rounded-md object-cover border border-gray-700 bg-gray-800"
                          />
                        ) : (
                          <div className="w-10 h-10 rounded-md border border-gray-700 bg-gray-800" />
                        )}
                        <span className="text-gray-300 font-mono text-xs">{shortId(r.id)}</span>
                      </div>
                    </td>
                    <td className="px-5 py-4 text-gray-300 capitalize">{r.category}</td>
                    <td className="px-5 py-4 text-gray-400 max-w-[280px]">
                      <p className="line-clamp-2">{r.description}</p>
                    </td>
                    <td className="px-5 py-4 text-gray-400 whitespace-nowrap">{formatDate(r.created_at)}</td>
                    <td className="px-5 py-4 text-gray-400 font-mono text-xs">{r.incident_id ? shortId(r.incident_id) : '—'}</td>
                    <td className="px-5 py-4">
                      <Link to={`/admin/reports/${r.id}`} className="text-brand-400 hover:text-brand-300 underline underline-offset-2">
                        View
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </AdminLayout>
  );
}
