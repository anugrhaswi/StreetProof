import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { AlertCircle, ArrowLeft, Calendar, ExternalLink, FileText, ImageOff, Loader2, MapPin } from 'lucide-react';
import { getIncident, imageUrl, type Incident, type Report } from '../services/api';

const CATEGORY_LABELS: Record<string, string> = {
  pothole: 'Pothole',
  streetlight: 'Streetlight',
  garbage: 'Garbage',
  graffiti: 'Graffiti',
  sidewalk: 'Sidewalk',
  signage: 'Signage',
  drainage: 'Drainage',
  other: 'Other',
};

const STATUS_STYLES: Record<string, string> = {
  open: 'bg-red-500/15 text-red-400 border-red-500/30',
  closed: 'bg-green-500/15 text-green-400 border-green-500/30',
  merged: 'bg-gray-500/15 text-gray-400 border-gray-500/30',
};

const STATUS_LABELS: Record<string, string> = {
  open: 'Open',
  closed: 'Closed',
  merged: 'Merged',
};

function formatDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return 'Unknown date';
  return d.toLocaleString();
}

function ReportEvidenceCard({ report }: { report: Report }) {
  const [imgError, setImgError] = useState(false);

  return (
    <article className="rounded-xl border border-gray-800 bg-gray-900/30 overflow-hidden">
      <div className="aspect-[16/10] bg-gray-900 flex items-center justify-center border-b border-gray-800">
        {imgError ? (
          <div className="flex flex-col items-center text-gray-500 text-sm gap-2">
            <ImageOff size={24} />
            <span>Image unavailable</span>
          </div>
        ) : (
          <img
            src={imageUrl(report.image_path)}
            alt={`Report evidence ${report.id.slice(0, 8)}`}
            className="w-full h-full object-cover"
            loading="lazy"
            onError={() => setImgError(true)}
          />
        )}
      </div>
      <div className="p-4">
        <div className="flex items-center justify-between gap-2 mb-2">
          <span className="text-xs text-gray-500 font-mono">Report {report.id.slice(0, 8)}…</span>
          <span className="text-xs text-gray-500">{formatDate(report.created_at)}</span>
        </div>
        <p className="text-sm text-gray-300 leading-relaxed whitespace-pre-wrap">{report.description}</p>
        <div className="mt-3 text-xs text-gray-500 flex items-center gap-1.5">
          <MapPin size={12} />
          <span>{report.latitude.toFixed(5)}, {report.longitude.toFixed(5)}</span>
        </div>
      </div>
    </article>
  );
}

export default function IncidentDetail() {
  const { id } = useParams<{ id: string }>();
  const [incident, setIncident] = useState<Incident | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) {
      setError('Missing incident ID.');
      setLoading(false);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    getIncident(id)
      .then((data) => {
        if (!cancelled) setIncident(data);
      })
      .catch((err) => {
        console.error('[IncidentDetail] Failed to load incident', err);
        if (!cancelled) setError(err instanceof Error ? err.message : 'Failed to load incident.');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, [id]);

  if (loading) {
    return (
      <div className="max-w-5xl mx-auto px-6 py-16 flex items-center justify-center text-gray-400">
        <Loader2 className="animate-spin mr-2" size={20} /> Loading incident…
      </div>
    );
  }

  if (error || !incident) {
    return (
      <div className="max-w-5xl mx-auto px-6 py-16">
        <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-6 text-center">
          <AlertCircle className="mx-auto mb-3 text-red-400" size={24} />
          <p className="text-red-300 font-medium mb-1">Unable to load incident</p>
          <p className="text-red-300/80 text-sm mb-4">{error || 'Incident not found.'}</p>
          <Link to="/map" className="text-brand-400 hover:text-brand-300 text-sm">← Back to map</Link>
        </div>
      </div>
    );
  }

  const reports = incident.reports ?? [];
  const statusStyle = STATUS_STYLES[incident.status] ?? STATUS_STYLES.open;
  const statusLabel = STATUS_LABELS[incident.status] ?? incident.status;
  const categoryLabel = CATEGORY_LABELS[incident.category] ?? incident.category;
  const hasValidCoords = Number.isFinite(incident.latitude) && Number.isFinite(incident.longitude)
    && incident.latitude >= -90 && incident.latitude <= 90 && incident.longitude >= -180 && incident.longitude <= 180;
  const googleMapsUrl = hasValidCoords
    ? `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(incident.latitude)},${encodeURIComponent(incident.longitude)}`
    : null;

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8">
      <Link to="/map" className="inline-flex items-center gap-1.5 text-sm text-gray-400 hover:text-white mb-6 transition-colors">
        <ArrowLeft size={16} /> Back to map
      </Link>

      {incident.status === 'merged' && incident.merged_into_incident_id && (
        <div className="mb-6 p-4 rounded-lg border border-amber-500/30 bg-amber-500/10 text-amber-200 text-sm">
          <p className="font-medium">This incident was merged into another incident.</p>
          <Link to={`/incidents/${incident.merged_into_incident_id}`} className="text-amber-300 underline hover:text-amber-200">
            View the surviving incident →
          </Link>
        </div>
      )}

      <div className="rounded-xl border border-gray-800 bg-gray-900/30 p-6 mb-6">
        <div className="flex flex-wrap items-start justify-between gap-4 mb-4">
          <div>
            <div className="flex flex-wrap items-center gap-2 mb-2">
              <span className="px-2.5 py-0.5 text-xs rounded-full bg-brand-500/10 text-brand-400 border border-brand-500/20">
                {categoryLabel}
              </span>
              <span className={`px-2.5 py-0.5 text-xs rounded-full border ${statusStyle}`}>
                {statusLabel}
              </span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-bold text-white">{incident.title}</h1>
          </div>
          <div className="text-xs text-gray-500 font-mono">ID: {incident.id}</div>
        </div>

        <p className="text-gray-300 leading-relaxed mb-6 whitespace-pre-wrap">{incident.description}</p>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-sm">
          <div className="flex items-start gap-2 text-gray-400">
            <MapPin size={16} className="mt-0.5 text-gray-500 shrink-0" />
            <div>
              <div className="text-gray-500 text-xs uppercase tracking-wide">Location</div>
              {googleMapsUrl ? (
                <a
                  href={googleMapsUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-brand-400 hover:text-brand-300 font-medium"
                >
                  Open in Google Maps <ExternalLink size={13} />
                </a>
              ) : (
                <div className="text-gray-500">Location unavailable</div>
              )}
              <div className="text-xs text-gray-500 mt-0.5">Coordinates: {incident.latitude.toFixed(5)}, {incident.longitude.toFixed(5)}</div>
            </div>
          </div>
          <div className="flex items-start gap-2 text-gray-400">
            <Calendar size={16} className="mt-0.5 text-gray-500 shrink-0" />
            <div>
              <div className="text-gray-500 text-xs uppercase tracking-wide">Created</div>
              <div className="text-gray-300">{formatDate(incident.created_at)}</div>
            </div>
          </div>
          <div className="flex items-start gap-2 text-gray-400">
            <FileText size={16} className="mt-0.5 text-gray-500 shrink-0" />
            <div>
              <div className="text-gray-500 text-xs uppercase tracking-wide">Reports</div>
              <div className="text-gray-300">{reports.length} associated report{reports.length !== 1 ? 's' : ''}</div>
            </div>
          </div>
        </div>
      </div>

      <section>
        <h2 className="text-lg font-semibold text-white mb-4">Associated Reports</h2>
        {reports.length === 0 ? (
          <div className="rounded-xl border border-gray-800 bg-gray-900/30 p-8 text-center text-gray-500">
            No reports associated with this incident.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {reports.map((report) => (
              <ReportEvidenceCard key={report.id} report={report} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
