import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, MapPin, Calendar, AlertCircle, ImageOff, Loader2 } from 'lucide-react';
import { getReport, imageUrl, type Report } from '../services/api';
import { useToast } from '../components/Toast';
import PotentialMatches from '../components/PotentialMatches';

const statusStyles: Record<string, string> = {
  open: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
  closed: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
  merged: 'bg-blue-500/10 text-blue-400 border-blue-500/30',
};

export default function ReportDetail() {
  const { id } = useParams<{ id: string }>();
  const toast = useToast();
  const [report, setReport] = useState<Report | null>(null);
  const [loading, setLoading] = useState(true);
  const [imgError, setImgError] = useState(false);

  useEffect(() => {
    if (!id) return;
    let active = true;
    setLoading(true);
    getReport(id)
      .then((data) => { if (active) setReport(data); })
      .catch((err) => { if (active) toast.error(err instanceof Error ? err.message : 'Failed to load report.'); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [id, toast]);

  if (loading) {
    return <div className="flex items-center justify-center py-24 text-gray-400"><Loader2 className="animate-spin mr-2" /> Loading...</div>;
  }

  if (!report) {
    return (
      <div className="max-w-3xl mx-auto px-6 py-16 text-center">
        <AlertCircle className="mx-auto mb-3 text-red-400" size={32} />
        <p className="text-gray-300 mb-4">Report not found.</p>
        <Link to="/reports" className="text-brand-400 hover:underline">Back to reports</Link>
      </div>
    );
  }

  const incident = report.incident;

  return (
    <div className="max-w-4xl mx-auto px-6 py-12">
      <Link to="/reports" className="inline-flex items-center gap-1.5 text-sm text-gray-400 hover:text-gray-200 mb-6">
        <ArrowLeft size={16} /> Back to reports
      </Link>

      <div className="grid md:grid-cols-2 gap-8">
        <div className="rounded-xl overflow-hidden border border-gray-800 bg-gray-900/40 min-h-[280px] flex items-center justify-center">
          {imgError ? (
            <div className="text-gray-500 flex flex-col items-center gap-2 py-20">
              <ImageOff size={32} />
              <span className="text-sm">Image unavailable</span>
            </div>
          ) : (
            <img
              src={imageUrl(report.image_path)}
              alt={report.description}
              className="w-full h-auto object-contain max-h-[480px]"
              onError={() => setImgError(true)}
            />
          )}
        </div>

        <div>
          <div className="flex items-center gap-2 mb-3">
            <span className="px-2.5 py-1 text-xs rounded-full bg-brand-500/10 text-brand-400 border border-brand-500/20 capitalize">
              {report.category}
            </span>
            {incident && (
              <span className={`px-2.5 py-1 text-xs rounded-full border capitalize ${statusStyles[incident.status] || 'text-gray-400 border-gray-600'}`}>
                {incident.status}
              </span>
            )}
          </div>

          <h1 className="text-2xl font-bold text-white mb-4">{incident?.title || 'Report Detail'}</h1>
          <p className="text-gray-300 leading-relaxed mb-6 whitespace-pre-wrap">{report.description}</p>

          <dl className="space-y-3 text-sm">
            <div className="flex gap-3">
              <MapPin size={16} className="text-gray-500 mt-0.5" />
              <div>
                <dt className="text-gray-500">Coordinates</dt>
                <dd className="text-gray-200">{report.latitude.toFixed(6)}, {report.longitude.toFixed(6)}</dd>
              </div>
            </div>
            <div className="flex gap-3">
              <Calendar size={16} className="text-gray-500 mt-0.5" />
              <div>
                <dt className="text-gray-500">Submitted</dt>
                <dd className="text-gray-200">{new Date(report.created_at).toLocaleString()}</dd>
              </div>
            </div>
            {incident && (
              <div className="pt-3 border-t border-gray-800">
                <dt className="text-gray-500 mb-1">Related Incident</dt>
                <dd className="text-gray-200">{incident.title}</dd>
                <dd className="text-xs text-gray-500 mt-1">ID: {incident.id}</dd>
              </div>
            )}
          </dl>
        </div>
      </div>

      <PotentialMatches reportId={report.id} />
    </div>
  );
}
