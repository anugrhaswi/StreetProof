import { Link } from 'react-router-dom';
import { MapPin, Calendar, ImageOff } from 'lucide-react';
import { useState } from 'react';
import type { Report } from '../services/api';
import { imageUrl } from '../services/api';

interface ReportCardProps {
  report: Report;
}

const categoryLabels: Record<string, string> = {
  pothole: 'Pothole',
  streetlight: 'Streetlight',
  garbage: 'Garbage',
  graffiti: 'Graffiti',
  sidewalk: 'Sidewalk',
  signage: 'Signage',
  drainage: 'Drainage',
  other: 'Other',
};

export default function ReportCard({ report }: ReportCardProps) {
  const [imgError, setImgError] = useState(false);

  return (
    <Link
      to={`/reports/${report.id}`}
      className="flex gap-4 p-4 rounded-xl border border-gray-800/70 bg-gray-900/30 hover:bg-gray-900/60 transition-colors"
    >
      <div className="w-[120px] h-[90px] flex-shrink-0 rounded-lg overflow-hidden bg-gray-800 border border-gray-700 flex items-center justify-center">
        {imgError ? (
          <div className="flex flex-col items-center text-gray-500 text-xs">
            <ImageOff size={20} />
            <span>Unavailable</span>
          </div>
        ) : (
          <img
            src={imageUrl(report.image_path)}
            alt={report.description.slice(0, 80)}
            width={120}
            height={90}
            className="w-[120px] h-[90px] object-cover"
            onError={() => setImgError(true)}
            loading="lazy"
          />
        )}
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <span className="px-2 py-0.5 text-xs rounded-full bg-brand-500/10 text-brand-400 border border-brand-500/20">
            {categoryLabels[report.category] || report.category}
          </span>
        </div>
        <p className="text-sm text-gray-200 line-clamp-2 mb-2">{report.description}</p>
        <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-gray-500">
          <span className="inline-flex items-center gap-1">
            <MapPin size={12} />
            {report.latitude.toFixed(4)}, {report.longitude.toFixed(4)}
          </span>
          <span className="inline-flex items-center gap-1">
            <Calendar size={12} />
            {new Date(report.created_at).toLocaleString()}
          </span>
        </div>
      </div>
    </Link>
  );
}
