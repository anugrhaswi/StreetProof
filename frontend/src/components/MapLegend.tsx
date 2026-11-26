import { Info } from 'lucide-react';

const CATEGORIES = [
  { key: 'pothole', label: 'Pothole' },
  { key: 'streetlight', label: 'Streetlight' },
  { key: 'garbage', label: 'Garbage' },
  { key: 'graffiti', label: 'Graffiti' },
  { key: 'sidewalk', label: 'Sidewalk' },
  { key: 'signage', label: 'Signage' },
  { key: 'drainage', label: 'Drainage' },
  { key: 'other', label: 'Other' },
];

export default function MapLegend() {
  return (
    <div className="bg-gray-900/95 border border-gray-800 rounded-xl p-4 backdrop-blur-sm">
      <p className="text-xs text-gray-500 uppercase tracking-wide mb-2">Status</p>
      <div className="flex items-center gap-4 mb-3 text-xs text-gray-300">
        <div className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded-full bg-red-500 border border-red-900" />
          <span>Open</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded-full bg-green-500 border border-green-900" />
          <span>Closed</span>
        </div>
      </div>

      <p className="text-xs text-gray-500 uppercase tracking-wide mb-2">Map guide</p>
      <div className="space-y-2 text-xs text-gray-400 mb-3">
        <div className="flex items-center gap-2">
          <span className="w-4 h-4 rounded-full bg-red-500 border border-red-900 shrink-0" />
          <span>Marker: a reported incident. Icon shows category, color shows status.</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-5 h-5 rounded-full bg-blue-600 border border-white/70 text-[10px] text-white inline-flex items-center justify-center shrink-0">3</span>
          <span>Cluster: nearby incidents grouped together. Click to zoom in.</span>
        </div>
        <div className="flex items-start gap-2">
          <Info size={14} className="text-gray-500 mt-0.5 shrink-0" />
          <span>Click a marker to open incident details. Use +/− or pinch to zoom.</span>
        </div>
      </div>

      <p className="text-xs text-gray-500 uppercase tracking-wide mb-2">Categories</p>
      <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-xs text-gray-400">
        {CATEGORIES.map((c) => (
          <div key={c.key} className="flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-gray-500" />
            <span>{c.label}</span>
          </div>
        ))}
      </div>
      <p className="text-[11px] text-gray-500 mt-3 leading-relaxed">
        Merged incidents are represented by their surviving incident.
      </p>
    </div>
  );
}
