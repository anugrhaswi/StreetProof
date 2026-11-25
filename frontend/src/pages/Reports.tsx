import { useEffect, useState } from 'react';
import { Loader2, ChevronLeft, ChevronRight } from 'lucide-react';
import ReportCard from '../components/ReportCard';
import { getReports, type Report } from '../services/api';
import { useToast } from '../components/Toast';

export default function Reports() {
  const toast = useToast();
  const [reports, setReports] = useState<Report[]>([]);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    setLoading(true);
    getReports(page, pageSize)
      .then((data) => {
        if (!active) return;
        setReports(data.items);
        setTotal(data.total);
        setTotalPages(data.total_pages);
      })
      .catch((err) => {
        if (active) toast.error(err instanceof Error ? err.message : 'Failed to load reports.');
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => { active = false; };
  }, [page, pageSize, toast]);

  return (
    <div className="max-w-5xl mx-auto px-6 py-12">
      <div className="flex items-end justify-between mb-8 gap-4 flex-wrap">
        <div>
          <h1 className="text-3xl font-bold text-white mb-1">Reports</h1>
          <p className="text-gray-400 text-sm">{total} total report{total !== 1 ? 's' : ''}</p>
        </div>
        <label className="text-sm text-gray-400 flex items-center gap-2">
          Per page
          <select
            value={pageSize}
            onChange={(e) => { setPage(1); setPageSize(Number(e.target.value)); }}
            className="bg-gray-900/60 border border-gray-700 rounded px-2 py-1 text-gray-200"
          >
            {[10, 20, 50, 100].map((n) => <option key={n} value={n}>{n}</option>)}
          </select>
        </label>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20 text-gray-400">
          <Loader2 className="animate-spin mr-2" size={20} /> Loading reports...
        </div>
      ) : reports.length === 0 ? (
        <div className="text-center py-20 text-gray-500 border border-dashed border-gray-800 rounded-xl">
          No reports yet. Submit one from the Report page.
        </div>
      ) : (
        <div className="space-y-4">
          {reports.map((r) => <ReportCard key={r.id} report={r} />)}
        </div>
      )}

      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-4 mt-8 text-sm">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page <= 1}
            className="inline-flex items-center gap-1 px-3 py-1.5 rounded border border-gray-700 text-gray-300 disabled:opacity-40 hover:bg-gray-800"
          >
            <ChevronLeft size={16} /> Prev
          </button>
          <span className="text-gray-400">Page {page} of {totalPages}</span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page >= totalPages}
            className="inline-flex items-center gap-1 px-3 py-1.5 rounded border border-gray-700 text-gray-300 disabled:opacity-40 hover:bg-gray-800"
          >
            Next <ChevronRight size={16} />
          </button>
        </div>
      )}
    </div>
  );
}
