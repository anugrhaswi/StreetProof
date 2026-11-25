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
        Marker icons show category; color shows status. Merged incidents are represented by their surviving incident.
      </p>
    </div>
  );
}
