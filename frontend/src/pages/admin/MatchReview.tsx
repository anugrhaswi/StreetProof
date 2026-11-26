import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { AlertCircle, Check, ChevronLeft, ChevronRight, Eye, ImageOff, Search, X } from 'lucide-react';
import AdminLayout from '../../components/admin/AdminLayout';
import ConfirmDialog from '../../components/admin/ConfirmDialog';
import { useToast } from '../../components/Toast';
import {
  ApiError,
  acceptAdminMatch,
  getAdminMatches,
  getAdminMergeEvents,
  imageUrl,
  rejectAdminMatch,
  reverseAdminMerge,
  type AdminMatchSuggestionListItem,
  type Category,
  type MergeEventListItem,
  type SuggestionStatus,
} from '../../services/api';

const STATUS_OPTIONS: { value: '' | SuggestionStatus; label: string }[] = [
  { value: 'pending', label: 'Pending review' },
  { value: 'auto_merged', label: 'Auto merged' },
  { value: 'rejected', label: 'Rejected' },
  { value: 'reviewed', label: 'Reviewed' },
  { value: 'superseded', label: 'Superseded' },
  { value: '', label: 'All statuses' },
];

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

function formatDate(iso: string) {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' });
}
function shortId(id: string) { return id.length > 8 ? `${id.slice(0, 8)}…` : id; }
function fmtPct(v: number | null) { return v == null ? '—' : `${Math.round(v * 100)}%`; }
function fmtMeters(v: number | null) { return v == null ? '—' : `${v.toFixed(1)}m`; }

function Signal({ label, value, ok }: { label: string; value: string; ok?: boolean | null }) {
  const tone = ok === true ? 'text-green-300 border-green-500/30 bg-green-500/10'
    : ok === false ? 'text-red-300 border-red-500/30 bg-red-500/10'
    : 'text-gray-300 border-gray-700 bg-gray-800/40';
  return (
    <div className={`rounded-lg border px-3 py-2 ${tone}`}>
      <p className="text-[11px] uppercase tracking-wide opacity-80">{label}</p>
      <p className="text-sm font-medium">{value}</p>
    </div>
  );
}

function MatchThumb({ path, sizeClass }: { path: string | null | undefined; sizeClass: string }) {
  const [err, setErr] = useState(false);
  if (!path || err) {
    return (
      <div className={`${sizeClass} rounded border border-gray-700 bg-gray-800 flex items-center justify-center text-gray-500`}>
        <ImageOff size={16} />
      </div>
    );
  }
  return <img src={imageUrl(path)} alt="" className={`${sizeClass} rounded object-cover border border-gray-700 bg-gray-800`} onError={() => setErr(true)} loading="lazy" />;
}

function ModalReportImage({ path }: { path: string | null | undefined }) {
  const [err, setErr] = useState(false);
  if (!path || err) {
    return (
      <div className="w-full h-64 bg-gray-800 flex flex-col items-center justify-center text-gray-500 gap-2">
        <ImageOff size={24} />
        <span className="text-sm">Image unavailable</span>
      </div>
    );
  }
  return <img src={imageUrl(path)} alt="" className="w-full h-64 object-cover bg-gray-800" onError={() => setErr(true)} />;
}

export default function MatchReview() {
  const toast = useToast();
  const [items, setItems] = useState<AdminMatchSuggestionListItem[]>([]);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [statusFilter, setStatusFilter] = useState<'' | SuggestionStatus>('pending');
  const [category, setCategory] = useState<'' | Category>('');
  const [classification, setClassification] = useState('');
  const [search, setSearch] = useState('');
  const [searchInput, setSearchInput] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [selected, setSelected] = useState<AdminMatchSuggestionListItem | null>(null);
  const [accepting, setAccepting] = useState(false);
  const [rejecting, setRejecting] = useState(false);
  const [confirmAccept, setConfirmAccept] = useState<AdminMatchSuggestionListItem | null>(null);
  const [confirmReject, setConfirmReject] = useState<AdminMatchSuggestionListItem | null>(null);
  const [rejectReason, setRejectReason] = useState('');

  const [merges, setMerges] = useState<MergeEventListItem[]>([]);
  const [mergeLoading, setMergeLoading] = useState(false);
  const [reverseTarget, setReverseTarget] = useState<MergeEventListItem | null>(null);
  const [reversing, setReversing] = useState(false);

  useEffect(() => {
    const t = window.setTimeout(() => { setPage(1); setSearch(searchInput.trim()); }, 300);
    return () => window.clearTimeout(t);
  }, [searchInput]);

  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const data = await getAdminMatches({
        page, page_size: pageSize,
        status: statusFilter || undefined,
        category: category || undefined,
        classification: classification || undefined,
        search: search || undefined,
      });
      setItems(data.items); setTotal(data.total); setTotalPages(data.total_pages);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load match suggestions.');
    } finally { setLoading(false); }
  }, [page, pageSize, statusFilter, category, classification, search]);

  const loadMerges = useCallback(async () => {
    setMergeLoading(true);
    try {
      const data = await getAdminMergeEvents(1, 10);
      setMerges(data.items);
    } catch { /* non-fatal */ } finally { setMergeLoading(false); }
  }, []);

  useEffect(() => { void load(); }, [load]);
  useEffect(() => { void loadMerges(); }, [loadMerges]);

  const refreshAfterAction = async (closedId?: string) => {
    if (closedId && selected?.id === closedId) setSelected(null);
    await Promise.all([load(), loadMerges()]);
  };

  const onAccept = async () => {
    if (!confirmAccept) return;
    setAccepting(true);
    try {
      await acceptAdminMatch(confirmAccept.id);
      toast.success('Match accepted and incidents merged.');
      setConfirmAccept(null);
      await refreshAfterAction(confirmAccept.id);
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) toast.error(`Cannot accept: ${err.message}`);
      else toast.error(err instanceof Error ? err.message : 'Failed to accept match.');
    } finally { setAccepting(false); }
  };

  const onReject = async () => {
    if (!confirmReject) return;
    setRejecting(true);
    try {
      await rejectAdminMatch(confirmReject.id, rejectReason.trim() || undefined);
      toast.success('Match rejected.');
      setConfirmReject(null); setRejectReason('');
      await refreshAfterAction(confirmReject.id);
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) toast.error(`Cannot reject: ${err.message}`);
      else toast.error(err instanceof Error ? err.message : 'Failed to reject match.');
    } finally { setRejecting(false); }
  };

  const onReverse = async () => {
    if (!reverseTarget) return;
    setReversing(true);
    try {
      await reverseAdminMerge(reverseTarget.id);
      toast.success('Merge reversed.');
      setReverseTarget(null);
      await refreshAfterAction();
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) toast.error(`Cannot reverse: ${err.message}`);
      else toast.error(err instanceof Error ? err.message : 'Failed to reverse merge.');
    } finally { setReversing(false); }
  };

  return (
    <AdminLayout title="AI Match Review">
      <div className="space-y-6">
        <div className="bg-gray-900/50 border border-gray-800 rounded-xl overflow-hidden">
          <div className="p-4 sm:p-5 border-b border-gray-800 space-y-4">
            <div className="flex flex-col sm:flex-row gap-3 sm:items-center sm:justify-between">
              <p className="text-sm text-gray-400">{total} suggestion{total !== 1 ? 's' : ''}</p>
              <div className="relative w-full sm:w-72">
                <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
                <input value={searchInput} onChange={(e) => setSearchInput(e.target.value)} placeholder="Search suggestion/report/incident ID..." className="w-full pl-9 pr-3 py-2 rounded-lg bg-gray-950 border border-gray-700 text-sm text-gray-100 focus:outline-none focus:ring-2 focus:ring-brand-500/40" />
              </div>
            </div>
            <div className="flex flex-col sm:flex-row gap-3">
              <select value={statusFilter} onChange={(e) => { setPage(1); setStatusFilter(e.target.value as '' | SuggestionStatus); }} className="bg-gray-950 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200">
                {STATUS_OPTIONS.map((s) => <option key={s.value || 'all'} value={s.value}>{s.label}</option>)}
              </select>
              <select value={category} onChange={(e) => { setPage(1); setCategory(e.target.value as '' | Category); }} className="bg-gray-950 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200">
                {CATEGORIES.map((c) => <option key={c.value || 'all'} value={c.value}>{c.label}</option>)}
              </select>
              <select value={classification} onChange={(e) => { setPage(1); setClassification(e.target.value); }} className="bg-gray-950 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200">
                <option value="">All classifications</option>
                <option value="REVIEW_CANDIDATE">Review candidate</option>
                <option value="AUTO_MERGE_CANDIDATE">Auto-merge candidate</option>
              </select>
              <select value={pageSize} onChange={(e) => { setPage(1); setPageSize(Number(e.target.value)); }} className="bg-gray-950 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 sm:ml-auto">
                {[10, 20, 50].map((n) => <option key={n} value={n}>{n} / page</option>)}
              </select>
            </div>
          </div>

          {error && (
            <div className="m-4 p-4 rounded-lg border border-red-500/30 bg-red-500/10 text-red-200 flex items-center justify-between gap-4 text-sm">
              <div className="flex items-center gap-2"><AlertCircle size={16} /><span>{error}</span></div>
              <button onClick={() => void load()} className="underline">Retry</button>
            </div>
          )}

          {loading ? (
            <div className="p-5 space-y-3">{Array.from({ length: 5 }).map((_, i) => <div key={i} className="h-20 bg-gray-800/50 rounded-lg animate-pulse" />)}</div>
          ) : items.length === 0 ? (
            <div className="p-10 text-center text-gray-400 text-sm">No match suggestions found.</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="text-left text-gray-400 bg-gray-900/80">
                  <tr>
                    <th className="px-5 py-3 font-medium">Reports</th>
                    <th className="px-5 py-3 font-medium">Signals</th>
                    <th className="px-5 py-3 font-medium">Classification</th>
                    <th className="px-5 py-3 font-medium">Status</th>
                    <th className="px-5 py-3 font-medium">Created</th>
                    <th className="px-5 py-3 font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((s) => (
                    <tr key={s.id} className="border-t border-gray-800/80 align-top">
                      <td className="px-5 py-4">
                        <div className="flex items-center gap-3">
                          <MatchThumb path={s.report.image_path} sizeClass="w-12 h-12" />
                          <div className="text-xs text-gray-500">vs</div>
                          <MatchThumb path={s.matched_report.image_path} sizeClass="w-12 h-12" />
                          <div className="min-w-0">
                            <p className="text-gray-300 font-mono text-xs">{shortId(s.report_id)}  {shortId(s.matched_report_id)}</p>
                            <p className="text-gray-500 text-xs capitalize">{s.report.category}</p>
                          </div>
                        </div>
                      </td>
                      <td className="px-5 py-4 text-xs text-gray-400 space-y-1">
                        <div>Text {fmtPct(s.text_similarity)} · pHash {fmtPct(s.phash_similarity)}</div>
                        <div>Geo {fmtMeters(s.geo_distance_meters)} · Cat {s.category_match == null ? '—' : s.category_match ? 'match' : 'diff'}</div>
                      </td>
                      <td className="px-5 py-4"><span className="text-xs px-2 py-1 rounded-full border border-gray-700 text-gray-300">{s.candidate_classification ?? '—'}</span></td>
                      <td className="px-5 py-4"><span className="text-xs px-2 py-1 rounded-full border border-gray-700 text-gray-300 capitalize">{s.status.replace('_', ' ')}</span></td>
                      <td className="px-5 py-4 text-gray-400 whitespace-nowrap">{formatDate(s.created_at)}</td>
                      <td className="px-5 py-4">
                        <div className="flex items-center gap-2">
                          <button onClick={() => setSelected(s)} className="p-2 rounded-md border border-gray-700 text-gray-300 hover:text-white" aria-label="Review"><Eye size={15} /></button>
                          {(s.status === 'pending' || s.status === 'reviewed') && (
                            <>
                              <button onClick={() => setConfirmAccept(s)} className="p-2 rounded-md border border-green-500/30 text-green-300 hover:bg-green-500/10" aria-label="Accept"><Check size={15} /></button>
                              <button onClick={() => { setConfirmReject(s); setRejectReason(''); }} className="p-2 rounded-md border border-red-500/30 text-red-300 hover:bg-red-500/10" aria-label="Reject"><X size={15} /></button>
                            </>
                          )}
                        </div>
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

        <div className="bg-gray-900/50 border border-gray-800 rounded-xl overflow-hidden">
          <div className="p-4 sm:p-5 border-b border-gray-800">
            <h2 className="text-sm font-semibold text-white">Automatic Merge History</h2>
            <p className="text-xs text-gray-500 mt-1">Recent merge events. Reversal is conservative and may be refused if unsafe.</p>
          </div>
          {mergeLoading ? <div className="p-5"><div className="h-16 bg-gray-800/50 rounded animate-pulse" /></div>
            : merges.length === 0 ? <div className="p-6 text-sm text-gray-500">No merge events yet.</div>
            : <div className="divide-y divide-gray-800">
                {merges.map((m) => (
                  <div key={m.id} className="p-4 sm:px-5 flex flex-col sm:flex-row sm:items-center gap-3 justify-between">
                    <div className="text-sm">
                      <p className="text-gray-200"><span className="font-mono text-xs text-gray-400">{shortId(m.id)}</span> · {m.action} · <span className="capitalize">{m.actor}</span></p>
                      <p className="text-xs text-gray-500 mt-1">Report {shortId(m.report_id)} → incident {shortId(m.target_incident_id)} · {formatDate(m.created_at)}</p>
                      {m.reversed_at && <p className="text-xs text-amber-300 mt-1">Reversed {formatDate(m.reversed_at)}</p>}
                    </div>
                    {m.action !== 'MERGE_REVERSAL' && !m.reversed_at && (
                      <button onClick={() => setReverseTarget(m)} className="px-3 py-1.5 rounded-md border border-amber-500/30 text-amber-300 text-xs hover:bg-amber-500/10 self-start">Undo merge</button>
                    )}
                  </div>
                ))}
              </div>}
        </div>
      </div>

      {selected && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/70" onClick={() => setSelected(null)} />
          <div className="relative w-full max-w-6xl max-h-[90vh] overflow-y-auto bg-gray-900 border border-gray-700 rounded-xl shadow-2xl">
            <div className="p-5 border-b border-gray-800 flex items-start justify-between gap-4">
              <div>
                <h3 className="text-lg font-semibold text-white">Match Comparison</h3>
                <p className="text-xs text-gray-500 font-mono mt-1">{selected.id}</p>
              </div>
              <button onClick={() => setSelected(null)} className="text-gray-400 hover:text-white p-1"><X size={18} /></button>
            </div>
            <div className="p-5 grid grid-cols-1 lg:grid-cols-2 gap-5">
              {[{ label: 'Report A', r: selected.report }, { label: 'Report B', r: selected.matched_report }].map(({ label, r }) => (
                <div key={r.id} className="bg-gray-950/40 border border-gray-800 rounded-lg overflow-hidden">
                  <div className="px-4 py-3 border-b border-gray-800 flex items-center justify-between">
                    <div><p className="text-sm font-medium text-white">{label}</p><p className="text-xs text-gray-500 font-mono">{r.id}</p></div>
                    <Link to={`/admin/reports/${r.id}`} className="text-xs text-brand-300 hover:text-brand-200 underline">Open report</Link>
                  </div>
                  <ModalReportImage path={r.image_path} />
                  <div className="p-4 space-y-2 text-sm">
                    <p className="text-gray-300">{r.description}</p>
                    <p className="text-gray-500 text-xs">Category: <span className="capitalize text-gray-300">{r.category}</span></p>
                    <p className="text-gray-500 text-xs">Coords: <span className="text-gray-300">{r.latitude.toFixed(5)}, {r.longitude.toFixed(5)}</span></p>
                    <p className="text-gray-500 text-xs">Incident: <span className="font-mono text-gray-300">{shortId(r.incident_id)}</span></p>
                    <p className="text-gray-500 text-xs">Submitted: <span className="text-gray-300">{formatDate(r.created_at)}</span></p>
                  </div>
                </div>
              ))}
            </div>
            <div className="px-5 pb-5">
              <div className="bg-gray-950/40 border border-gray-800 rounded-lg p-4">
                <h4 className="text-sm font-medium text-white mb-3">AI Match Signals</h4>
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
                  <Signal label="pHash" value={fmtPct(selected.phash_similarity)} ok={selected.phash_similarity == null ? null : selected.phash_similarity >= 0.65} />
                  <Signal label="Text" value={fmtPct(selected.text_similarity)} ok={selected.text_similarity == null ? null : selected.text_similarity >= 0.75} />
                  <Signal label="Geo" value={fmtMeters(selected.geo_distance_meters)} ok={selected.geo_distance_meters == null ? null : selected.geo_distance_meters <= 500} />
                  <Signal label="Category" value={selected.category_match == null ? '—' : selected.category_match ? 'Match' : 'Different'} ok={selected.category_match} />
                  <Signal label="SHA-256" value={selected.sha256_match == null ? '—' : selected.sha256_match ? 'Exact' : 'Different'} ok={selected.sha256_match} />
                  <Signal label="Score" value={fmtPct(selected.similarity_score)} ok={selected.similarity_score >= 0.75} />
                </div>
                <p className="text-xs text-gray-400 mt-4">
                  AI suggested this as <span className="text-gray-200">{selected.candidate_classification ?? 'a candidate'}</span> because the reports share similar {selected.category_match ? 'category, ' : ''}{selected.text_similarity != null ? 'description semantics, ' : ''}{selected.phash_similarity != null ? 'visual fingerprint, ' : ''}{selected.geo_distance_meters != null ? 'and nearby location' : 'signals'}.
                </p>
              </div>
            </div>
            {(selected.status === 'pending' || selected.status === 'reviewed') && (
              <div className="px-5 pb-5 flex flex-col sm:flex-row gap-3 justify-end border-t border-gray-800 pt-4">
                <button onClick={() => { setConfirmReject(selected); setRejectReason(''); }} className="px-4 py-2 rounded-lg border border-red-500/30 text-red-300 hover:bg-red-500/10 text-sm">Reject Match</button>
                <button onClick={() => setConfirmAccept(selected)} className="px-4 py-2 rounded-lg bg-green-600 hover:bg-green-500 text-white text-sm font-medium">Accept Match</button>
              </div>
            )}
          </div>
        </div>
      )}

      <ConfirmDialog
        open={!!confirmAccept}
        title="Accept match?"
        message={confirmAccept ? `This will merge report ${shortId(confirmAccept.report_id)} into incident ${shortId(confirmAccept.incident_id)}. The merge is recorded and reversible if safe.` : ''}
        confirmLabel="Accept and merge"
        loading={accepting}
        onConfirm={() => void onAccept()}
        onCancel={() => { if (!accepting) setConfirmAccept(null); }}
      />

      {confirmReject && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/60" onClick={() => { if (!rejecting) setConfirmReject(null); }} />
          <div className="relative w-full max-w-md bg-gray-900 border border-gray-700 rounded-xl p-6 shadow-2xl">
            <h3 className="text-lg font-semibold text-white mb-2">Reject match?</h3>
            <p className="text-sm text-gray-400 mb-4">This marks the suggestion as rejected. Reports will not be merged.</p>
            <label className="block text-sm text-gray-300 mb-1">Reason (optional)</label>
            <textarea value={rejectReason} onChange={(e) => setRejectReason(e.target.value)} maxLength={500} rows={3} className="w-full px-3 py-2 rounded-lg bg-gray-950 border border-gray-700 text-sm text-gray-100 focus:outline-none focus:ring-2 focus:ring-brand-500/40" />
            <div className="flex justify-end gap-3 mt-4">
              <button onClick={() => { if (!rejecting) setConfirmReject(null); }} className="px-4 py-2 rounded-lg border border-gray-700 text-gray-300 text-sm" disabled={rejecting}>Cancel</button>
              <button onClick={() => void onReject()} className="px-4 py-2 rounded-lg bg-red-600 hover:bg-red-500 text-white text-sm font-medium disabled:opacity-50" disabled={rejecting}>{rejecting ? 'Rejecting...' : 'Reject match'}</button>
            </div>
          </div>
        </div>
      )}

      <ConfirmDialog
        open={!!reverseTarget}
        title="Undo automatic merge?"
        message={reverseTarget ? `This will attempt to reverse merge ${shortId(reverseTarget.id)}. The system will refuse if the incident state is no longer safe to reverse.` : ''}
        confirmLabel="Undo merge"
        loading={reversing}
        onConfirm={() => void onReverse()}
        onCancel={() => { if (!reversing) setReverseTarget(null); }}
      />
    </AdminLayout>
  );
}
