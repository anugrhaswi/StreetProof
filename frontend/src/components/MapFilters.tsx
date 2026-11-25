import { Filter, X } from 'lucide-react';
import type { Category, Status } from '../services/api';
import type { MapFiltersState } from './IncidentMap';

interface MapFiltersProps {
  filters: MapFiltersState;
  onFiltersChange: (filters: MapFiltersState) => void;
  totalCount: number;
  filteredCount: number;
}

const CATEGORIES: { value: Category; label: string }[] = [
  { value: 'pothole', label: 'Pothole' },
  { value: 'streetlight', label: 'Streetlight' },
  { value: 'garbage', label: 'Garbage' },
  { value: 'graffiti', label: 'Graffiti' },
  { value: 'sidewalk', label: 'Sidewalk' },
  { value: 'signage', label: 'Signage' },
  { value: 'drainage', label: 'Drainage' },
  { value: 'other', label: 'Other' },
];

const STATUSES: { value: Status; label: string; color: string }[] = [
  { value: 'open', label: 'Open', color: '#ef4444' },
  { value: 'closed', label: 'Closed', color: '#22c55e' },
];

export default function MapFilters({ filters, onFiltersChange, totalCount, filteredCount }: MapFiltersProps) {
  const toggleCategory = (cat: Category) => {
    const next = new Set(filters.categories);
    if (next.has(cat)) next.delete(cat);
    else next.add(cat);
    onFiltersChange({ ...filters, categories: next });
  };

  const toggleStatus = (status: Status) => {
    const next = new Set(filters.statuses);
    if (next.has(status)) next.delete(status);
    else next.add(status);
    onFiltersChange({ ...filters, statuses: next });
  };

  const clearAll = () => {
    onFiltersChange({
      categories: new Set(CATEGORIES.map((c) => c.value)),
      statuses: new Set(STATUSES.map((s) => s.value)),
    });
  };

  const hasActiveFilters = filters.categories.size !== CATEGORIES.length || filters.statuses.size !== STATUSES.length;

  return (
    <div className="bg-gray-900/95 border border-gray-800 rounded-xl p-4 backdrop-blur-sm">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2 text-white font-medium text-sm">
          <Filter size={16} className="text-brand-400" />
          <span>Filters</span>
        </div>
        {hasActiveFilters && (
          <button
            onClick={clearAll}
            className="text-xs text-gray-400 hover:text-white flex items-center gap-1 transition-colors"
          >
            <X size={12} /> Clear all
          </button>
        )}
      </div>

      <div className="mb-4">
        <p className="text-xs text-gray-500 uppercase tracking-wide mb-2">Status</p>
        <div className="flex flex-wrap gap-2">
          {STATUSES.map((s) => {
            const active = filters.statuses.has(s.value);
            return (
              <button
                key={s.value}
                onClick={() => toggleStatus(s.value)}
                className={`px-2.5 py-1 text-xs rounded-full border transition-colors ${
                  active
                    ? 'border-transparent text-white'
                    : 'border-gray-700 text-gray-500 bg-transparent'
                }`}
                style={active ? { backgroundColor: s.color + '33', color: s.color, borderColor: s.color + '55' } : undefined}
              >
                {s.label}
              </button>
            );
          })}
        </div>
      </div>

      <div>
        <p className="text-xs text-gray-500 uppercase tracking-wide mb-2">Category</p>
        <div className="flex flex-wrap gap-1.5">
          {CATEGORIES.map((c) => {
            const active = filters.categories.has(c.value);
            return (
              <button
                key={c.value}
                onClick={() => toggleCategory(c.value)}
                className={`px-2 py-1 text-xs rounded-md border transition-colors ${
                  active
                    ? 'bg-brand-500/15 text-brand-300 border-brand-500/30'
                    : 'border-gray-800 text-gray-500 hover:text-gray-300'
                }`}
              >
                {c.label}
              </button>
            );
          })}
        </div>
      </div>

      <div className="mt-4 pt-3 border-t border-gray-800 text-xs text-gray-400">
        Showing <span className="text-white font-medium">{filteredCount}</span> of{' '}
        <span className="text-white font-medium">{totalCount}</span> incidents
      </div>
    </div>
  );
}
