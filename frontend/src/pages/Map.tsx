import { AlertCircle, Loader2, RefreshCw } from 'lucide-react';
import IncidentMap from '../components/IncidentMap';
import MapFilters from '../components/MapFilters';
import MapLegend from '../components/MapLegend';
import { useIncidentMapData } from '../hooks/useIncidentMapData';

export default function MapPage() {
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
  } = useIncidentMapData();

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
      <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4 mb-6">
        <div>
          <p className="text-brand-400 text-sm font-medium tracking-wide uppercase mb-1">Civic Map</p>
          <h1 className="text-2xl sm:text-3xl font-bold text-white">Incident Map</h1>
          <p className="text-gray-400 text-sm mt-1">
            Explore reported civic infrastructure issues across the community.
          </p>
        </div>
        <button
          onClick={refresh}
          disabled={loading}
          className="inline-flex items-center gap-2 px-3 py-2 text-sm rounded-lg border border-gray-700 text-gray-300 hover:text-white hover:border-gray-500 disabled:opacity-50 self-start"
        >
          <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
          Refresh
        </button>
      </div>

      {error && (
        <div className="mb-4 p-4 rounded-lg border border-red-500/30 bg-red-500/10 text-red-300 text-sm flex items-start gap-2">
          <AlertCircle size={16} className="mt-0.5 shrink-0" />
          <div>
            <p className="font-medium">Could not load incidents</p>
            <p className="text-red-300/80">{error}</p>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-[320px_1fr] gap-4">
        <div className="space-y-4 order-2 lg:order-1">
          <MapFilters
            filters={filters}
            onFiltersChange={setFilters}
            totalCount={incidents.length}
            filteredCount={filteredCount}
          />
          <MapLegend />
        </div>

        <div className="order-1 lg:order-2">
          <div className="relative rounded-xl border border-gray-800 bg-gray-900/30 h-[50vh] min-h-[400px] lg:h-[calc(100vh-220px)] lg:min-h-[560px]">
            {loading && incidents.length === 0 ? (
              <div className="h-full flex items-center justify-center text-gray-400">
                <Loader2 className="animate-spin mr-2" size={20} /> Loading incidents…
              </div>
            ) : (
              <>
                <IncidentMap
                  incidents={incidents}
                  filters={filters}
                  onIncidentSelect={(inc) => setSelectedIncidentId(inc.id)}
                  selectedIncidentId={selectedIncidentId}
                />
                {!loading && incidents.length === 0 && !error && (
                  <div className="absolute inset-x-0 top-4 mx-4 rounded-lg bg-gray-950/90 border border-gray-700 px-4 py-3 text-center z-10">
                    <p className="text-gray-300 font-medium text-sm">No incidents on the map yet</p>
                    <p className="text-xs text-gray-500">Submitted reports will appear here once incidents are created.</p>
                  </div>
                )}
                {!loading && incidents.length > 0 && filteredCount === 0 && (
                  <div className="absolute inset-x-0 top-4 mx-4 rounded-lg bg-gray-950/90 border border-gray-700 px-4 py-3 text-center z-10">
                    <p className="text-gray-300 font-medium text-sm">No incidents match your filters</p>
                    <p className="text-xs text-gray-500">Adjust or clear filters to see incidents on the map.</p>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
