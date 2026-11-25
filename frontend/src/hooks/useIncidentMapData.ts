import { useCallback, useEffect, useMemo, useState } from 'react';
import type { MapFiltersState } from '../components/IncidentMap';
import { getIncidentsForMap, type Category, type IncidentMapItem, type Status } from '../services/api';

const ALL_CATEGORIES: Category[] = ['pothole', 'streetlight', 'garbage', 'graffiti', 'sidewalk', 'signage', 'drainage', 'other'];
const ACTIVE_STATUSES: Status[] = ['open', 'closed'];

export const DEFAULT_MAP_FILTERS: MapFiltersState = {
  categories: new Set(ALL_CATEGORIES),
  statuses: new Set(ACTIVE_STATUSES),
};

function isValidCoord(lat: number, lng: number): boolean {
  return Number.isFinite(lat) && Number.isFinite(lng) && lat >= -90 && lat <= 90 && lng >= -180 && lng <= 180;
}

export function useIncidentMapData() {
  const [incidents, setIncidents] = useState<IncidentMapItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<MapFiltersState>(DEFAULT_MAP_FILTERS);
  const [selectedIncidentId, setSelectedIncidentId] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getIncidentsForMap();
      const valid = data.filter((inc) => {
        if (inc.status === 'merged') return false;
        if (!isValidCoord(inc.latitude, inc.longitude)) {
          console.warn('[Map] Invalid coordinates for incident', inc.id);
          return false;
        }
        return true;
      });
      setIncidents(valid);
    } catch (err) {
      console.error('[Map] Failed to load incidents', err);
      setError(err instanceof Error ? err.message : 'Failed to load incidents.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const filteredCount = useMemo(() => {
    return incidents.filter(
      (inc) => filters.categories.has(inc.category) && filters.statuses.has(inc.status),
    ).length;
  }, [incidents, filters]);

  const stats = useMemo(() => {
    const open = incidents.filter((i) => i.status === 'open').length;
    const closed = incidents.filter((i) => i.status === 'closed').length;
    const reports = incidents.reduce((sum, i) => sum + (i.report_count || 0), 0);
    return { total: incidents.length, open, closed, reports };
  }, [incidents]);

  return {
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
  };
}
