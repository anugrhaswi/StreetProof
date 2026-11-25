import { useState } from 'react';
import { AlertCircle, ChevronUp, Filter, Layers, Loader2, RefreshCw, X } from 'lucide-react';
import { Link } from 'react-router-dom';
import IncidentMap from '../components/IncidentMap';
import MapFilters from '../components/MapFilters';
import MapLegend from '../components/MapLegend';
import { useIncidentMapData } from '../hooks/useIncidentMapData';

export default function Home() {
  const {
    incidents,
    loading,
    error,
    filters,
    setFilters,
    filteredCount,
    selectedIncidentId,
    setSelectedIncidentId,
    refresh,
    stats,
  } = useIncidentMapData();
  const [panelOpen, setPanelOpen] = useState(false);

  return (
    <div className="relative h-full min-h-0 bg-brand-950">
      <div className="absolute inset-0">
        {loading && incidents.length === 0 ? (
          <div className="h-full flex items-center justify-center text-gray-400">
            <Loader2 className="animate-spin mr-2" size={20} /> Loading incidents…
          </div>
        ) : (
          <IncidentMap
            incidents={incidents}
            filters={filters}
            onIncidentSelect={(inc) => setSelectedIncidentId(inc.id)}
            selectedIncidentId={selectedIncidentId}
          />
        )}
      </div>

      {/* Top-left compact stats */}
      <div className="absolute top-3 left-3 sm:top-4 sm:left-4 z-20 w-[calc(100%-6rem)] max-w-xs">
        <div className="bg-gray-950/85 border border-gray-800 rounded-xl backdrop-blur-md shadow-lg p-3 sm:p-4">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <Layers size={15} className="text-brand-400" />
              <span className="text-xs font-medium text-gray-300 uppercase tracking-wide">Live incidents</span>
            </div>
            <button
              onClick={refresh}
              disabled={loading}
              className="text-gray-400 hover:text-white disabled:opacity-50"
              aria-label="Refresh incidents"
              title="Refresh"
            >
              <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            </button>
          </div>
          <div className="grid grid-cols-3 gap-2 text-center">
            <div className="rounded-lg bg-gray-900/70 px-2 py-2">
              <div className="text-lg font-semibold text-white leading-none">{stats.total}</div>
              <div className="text-[11px] text-gray-400 mt-1">Total</div>
            </div>
            <div className="rounded-lg bg-red-500/10 px-2 py-2">
              <div className="text-lg font-semibold text-red-400 leading-none">{stats.open}</div>
              <div className="text-[11px] text-gray-400 mt-1">Open</div>
            </div>
            <div className="rounded-lg bg-green-500/10 px-2 py-2">
              <div className="text-lg font-semibold text-green-400 leading-none">{stats.closed}</div>
              <div className="text-[11px] text-gray-400 mt-1">Closed</div>
            </div>
          </div>
          <div className="mt-2 text-[11px] text-gray-500 flex items-center justify-between">
            <span>{stats.reports} reports across incidents</span>
            <button
              onClick={() => setPanelOpen((v) => !v)}
              className="inline-flex items-center gap-1 text-gray-300 hover:text-white"
            >
              <Filter size={12} />
              Filters
            </button>
          </div>
        </div>
      </div>

      {/* Floating filter/legend panel */}
      {panelOpen && (
        <div className="absolute top-[152px] left-3 sm:left-4 z-20 w-[calc(100%-1.5rem)] sm:w-[340px] max-h-[calc(100%-170px)] overflow-auto">
          <div className="bg-gray-950/90 border border-gray-800 rounded-xl backdrop-blur-md shadow-xl p-3 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-white">Map filters</span>
              <button onClick={() => setPanelOpen(false)} className="text-gray-400 hover:text-white" aria-label="Close filters">
                <X size={16} />
              </button>
            </div>
            <MapFilters
              filters={filters}
              onFiltersChange={setFilters}
              totalCount={incidents.length}
              filteredCount={filteredCount}
            />
            <MapLegend />
          </div>
        </div>
      )}

      {/* Error/loading overlays */}
      {error && (
        <div className="absolute top-3 left-1/2 -translate-x-1/2 z-20 w-[calc(100%-2rem)] max-w-md">
          <div className="p-3 rounded-lg border border-red-500/30 bg-red-950/90 text-red-300 text-sm flex items-start gap-2 backdrop-blur">
            <AlertCircle size={16} className="mt-0.5 shrink-0" />
            <div>
              <p className="font-medium">Could not load incidents</p>
              <p className="text-red-300/80 text-xs">{error}</p>
            </div>
          </div>
        </div>
      )}

      {!loading && !error && incidents.length === 0 && (
        <div className="absolute bottom-20 left-1/2 -translate-x-1/2 z-20 w-[calc(100%-2rem)] max-w-md">
          <div className="rounded-lg bg-gray-950/90 border border-gray-700 px-4 py-3 text-center backdrop-blur">
            <p className="text-gray-300 font-medium text-sm">No incidents on the map yet</p>
            <p className="text-xs text-gray-500">Be the first to report an issue in your area.</p>
          </div>
        </div>
      )}

      {!loading && incidents.length > 0 && filteredCount === 0 && (
        <div className="absolute bottom-20 left-1/2 -translate-x-1/2 z-20 w-[calc(100%-2rem)] max-w-md">
          <div className="rounded-lg bg-gray-950/90 border border-gray-700 px-4 py-3 text-center backdrop-blur">
            <p className="text-gray-300 font-medium text-sm">No incidents match your filters</p>
            <p className="text-xs text-gray-500">Adjust or clear filters to see incidents.</p>
          </div>
        </div>
      )}

      {/* Mobile filter FAB / desktop hint */}
      <button
        onClick={() => setPanelOpen((v) => !v)}
        className="sm:hidden absolute bottom-4 left-4 z-20 inline-flex items-center gap-2 px-3 py-2 rounded-full bg-gray-950/90 border border-gray-700 text-gray-200 text-sm backdrop-blur shadow-lg"
        aria-label="Toggle filters"
      >
        {panelOpen ? <ChevronUp size={16} /> : <Filter size={16} />}
        {panelOpen ? 'Hide' : 'Filters'}
      </button>

      {/* Prominent but unobtrusive report action */}
      <Link
        to="/report"
        className="absolute bottom-4 right-4 z-20 inline-flex items-center gap-2 px-4 py-2.5 rounded-full bg-brand-500 hover:bg-brand-400 text-white text-sm font-medium shadow-lg shadow-brand-500/20 transition-colors"
      >
        Report Issue
      </Link>
    </div>
  );
}
