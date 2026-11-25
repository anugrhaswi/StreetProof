import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Map as MapLibreMap,
  NavigationControl,
  Popup,
  type CircleLayerSpecification,
  type GeoJSONSource,
  type LngLatLike,
  type SymbolLayerSpecification,
} from 'maplibre-gl';
import { setWorkerUrl } from 'maplibre-gl';
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url';
import { LocateFixed } from 'lucide-react';
import { MAP_CONFIG } from '../config/map';
import type { Category, IncidentMapItem, Status } from '../services/api';

setWorkerUrl(workerUrl);

export interface MapFiltersState {
  categories: Set<Category>;
  statuses: Set<Status>;
}

interface IncidentMapProps {
  incidents: IncidentMapItem[];
  filters: MapFiltersState;
  onIncidentSelect?: (incident: IncidentMapItem) => void;
  selectedIncidentId?: string | null;
}

type IncidentFeatureProperties = {
  id: string;
  title: string;
  description: string;
  category: Category;
  status: Status;
  report_count: number;
  created_at: string;
  latitude: number;
  longitude: number;
  iconImage: string;
  statusLabel: string;
};

const CATEGORY_ICONS: Record<Category, string> = {
  pothole: 'construction',
  streetlight: 'lamp',
  garbage: 'trash-2',
  graffiti: 'paintbrush',
  sidewalk: 'footprints',
  signage: 'signpost',
  drainage: 'droplets',
  other: 'map-pin',
};

// Lucide icon SVG paths (24x24 viewBox, stroke-based)
const ICON_PATHS: Record<string, string> = {
  'construction': '<rect x="2" y="6" width="20" height="8" rx="1"/><path d="M17 14v7"/><path d="M7 14v7"/><path d="M17 3v3"/><path d="M7 3v3"/><path d="M10 14 2.3 6.3"/><path d="m14 6 7.7 7.7"/><path d="m8 6 8 8"/>',
  'lamp': '<path d="M8 2h8l4 10H4L8 2Z"/><path d="M12 12v6"/><path d="M8 22v-2c0-1.1.9-2 2-2h4a2 2 0 0 1 2 2v2H8Z"/>',
  'trash-2': '<path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/><line x1="10" x2="10" y1="11" y2="17"/><line x1="14" x2="14" y1="11" y2="17"/>',
  'paintbrush': '<path d="m14.622 17.897-10.68-2.913"/><path d="M18.376 2.622a1 1 0 1 1 3.002 3.002L17.36 9.643a.5.5 0 0 0 0 .707l.944.944a2.41 2.41 0 0 1 0 3.408l-.944.944a.5.5 0 0 1-.707 0L8.354 7.348a.5.5 0 0 1 0-.707l.944-.944a2.41 2.41 0 0 1 3.408 0l.944.944a.5.5 0 0 0 .707 0z"/><path d="M9 8c-1.804 2.71-3.97 3.46-6.583 3.948a.507.507 0 0 0-.302.819l7.32 8.883a1 1 0 0 0 1.185.204C12.735 20.405 16 16.792 16 15"/>',
  'footprints': '<path d="M4 16v-2.38C4 11.5 2.97 10.5 3 8c.03-2.72 1.49-6 4.5-6C9.37 2 10 3.8 10 5.5c0 3.11-2 5.66-2 8.68V16a2 2 0 1 1-4 0Z"/><path d="M20 20v-2.38c0-2.12 1.03-3.12 1-5.62-.03-2.72-1.49-6-4.5-6C14.63 6 14 7.8 14 9.5c0 3.11 2 5.66 2 8.68V20a2 2 0 1 0 4 0Z"/><path d="M16 17h4"/><path d="M4 13h4"/>',
  'signpost': '<path d="M12 13v8"/><path d="M12 3v3"/><path d="M4 6a1 1 0 0 0-1 1v5a1 1 0 0 0 1 1h13a2 2 0 0 0 1.152-.365l3.424-2.317a1 1 0 0 0 0-1.635l-3.424-2.318A2 2 0 0 0 17 6z"/>',
  'droplets': '<path d="M7 16.3c2.2 0 4-1.83 4-4.05 0-1.16-.57-2.26-1.71-3.19S7.29 6.75 7 5.3c-.29 1.45-1.14 2.84-2.29 3.76S3 11.1 3 12.25c0 2.22 1.8 4.05 4 4.05z"/><path d="M12.56 6.6A10.97 10.97 0 0 0 14 3.02c.5 2.5 2 4.9 4 6.5s3 3.5 3 5.5a6.98 6.98 0 0 1-11.91 4.97"/>',
  'map-pin': '<path d="M20 10c0 4.993-5.539 10.193-7.399 11.799a1 1 0 0 1-1.202 0C9.539 20.193 4 14.993 4 10a8 8 0 0 1 16 0"/><circle cx="12" cy="10" r="3"/>',
};

const STATUS_COLORS: Record<Status, { fill: string; stroke: string; label: string }> = {
  open: { fill: '#ef4444', stroke: '#7f1d1d', label: 'Open' },
  closed: { fill: '#22c55e', stroke: '#14532d', label: 'Closed' },
  merged: { fill: '#6b7280', stroke: '#374151', label: 'Merged' },
};

const CATEGORY_LABELS: Record<Category, string> = {
  pothole: 'Pothole',
  streetlight: 'Streetlight',
  garbage: 'Garbage',
  graffiti: 'Graffiti',
  sidewalk: 'Sidewalk',
  signage: 'Signage',
  drainage: 'Drainage',
  other: 'Other',
};

function statusLabel(status: Status): string {
  return STATUS_COLORS[status]?.label ?? status;
}

function isValidCoord(lat: number, lng: number): boolean {
  return Number.isFinite(lat) && Number.isFinite(lng) && lat >= -90 && lat <= 90 && lng >= -180 && lng <= 180;
}

function createMarkerImageElement(category: Category, status: Status, size = 36): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const iconName = CATEGORY_ICONS[category] ?? 'map-pin';
    const paths = ICON_PATHS[iconName] ?? ICON_PATHS['map-pin'];
    const colors = STATUS_COLORS[status] ?? STATUS_COLORS.open;
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">
      <circle cx="${size / 2}" cy="${size / 2}" r="${size / 2 - 2}" fill="${colors.fill}" stroke="${colors.stroke}" stroke-width="2.5"/>
      <g transform="translate(${size / 2 - 8}, ${size / 2 - 8}) scale(0.667)" fill="none" stroke="white" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
        ${paths}
      </g>
    </svg>`;
    const img = new Image(size, size);
    img.onload = () => resolve(img);
    img.onerror = () => reject(new Error(`Failed to load marker icon: ${category}-${status}`));
    img.src = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svg);
  });
}

function iconImageId(category: Category, status: Status): string {
  return `incident-${category}-${status}`;
}

function toFeatureCollection(incidents: IncidentMapItem[], filters: MapFiltersState) {
  const features = incidents
    .filter((inc) => {
      if (inc.status === 'merged') return false;
      if (!filters.categories.has(inc.category)) return false;
      if (!filters.statuses.has(inc.status)) return false;
      if (!isValidCoord(inc.latitude, inc.longitude)) {
        console.warn('[Map] Excluding incident with invalid coords', inc.id, inc.latitude, inc.longitude);
        return false;
      }
      return true;
    })
    .map((inc) => ({
      type: 'Feature' as const,
      geometry: {
        type: 'Point' as const,
        coordinates: [inc.longitude, inc.latitude] as [number, number],
      },
      properties: {
        id: inc.id,
        title: inc.title,
        description: inc.description,
        category: inc.category,
        status: inc.status,
        report_count: inc.report_count,
        created_at: inc.created_at,
        latitude: inc.latitude,
        longitude: inc.longitude,
        iconImage: iconImageId(inc.category, inc.status),
        statusLabel: statusLabel(inc.status),
      } satisfies IncidentFeatureProperties,
    }));

  return { type: 'FeatureCollection' as const, features };
}

export default function IncidentMap({ incidents, filters, onIncidentSelect, selectedIncidentId }: IncidentMapProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const popupRef = useRef<Popup | null>(null);
  const loadedRef = useRef(false);
  const iconsRegisteredRef = useRef(false);
  const initialLocateAttemptedRef = useRef(false);
  const [mapReady, setMapReady] = useState(false);
  const [mapError, setMapError] = useState<string | null>(null);
  const [locating, setLocating] = useState(false);

  const filteredData = useMemo(() => toFeatureCollection(incidents, filters), [incidents, filters]);

  const registerIcons = useCallback(async (map: MapLibreMap) => {
    if (iconsRegisteredRef.current) return;
    const statuses: Status[] = ['open', 'closed'];
    const categories: Category[] = ['pothole', 'streetlight', 'garbage', 'graffiti', 'sidewalk', 'signage', 'drainage', 'other'];
    const tasks: Promise<void>[] = [];
    for (const category of categories) {
      for (const status of statuses) {
        const id = iconImageId(category, status);
        if (map.hasImage(id)) continue;
        tasks.push(
          createMarkerImageElement(category, status)
            .then((img) => {
              if (!map.hasImage(id)) map.addImage(id, img, { pixelRatio: 1 });
            })
            .catch((err) => {
              console.warn('[Map] Failed to register icon', id, err);
            }),
        );
      }
    }
    await Promise.all(tasks);
    iconsRegisteredRef.current = true;
  }, []);

  const locateUser = useCallback((silent = false) => {
    const map = mapRef.current;
    if (!map || !navigator.geolocation) return;
    setLocating(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLocating(false);
        const lat = pos.coords.latitude;
        const lng = pos.coords.longitude;
        if (!Number.isFinite(lat) || !Number.isFinite(lng)) return;
        map.easeTo({ center: [lng, lat], zoom: Math.max(map.getZoom(), 14), duration: 900 });
      },
      () => {
        setLocating(false);
        if (!silent) {
          // Keep default center; no precise location stored or logged.
        }
      },
      { enableHighAccuracy: false, timeout: 8000, maximumAge: 60000 },
    );
  }, []);

  // Initialize map once
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    let cancelled = false;

    const map = new MapLibreMap({
      container: containerRef.current,
      style: MAP_CONFIG.tileStyleUrl,
      center: [MAP_CONFIG.defaultLng, MAP_CONFIG.defaultLat],
      zoom: MAP_CONFIG.defaultZoom,
      attributionControl: { compact: true },
    });

    map.addControl(new NavigationControl({ showCompass: false }), 'top-right');
    mapRef.current = map;

    map.on('error', (e) => {
      console.error('[Map] MapLibre error', e?.error ?? e);
      if (!loadedRef.current) setMapError('Failed to load the map. Please try refreshing.');
    });

    map.on('load', async () => {
      if (cancelled) return;
      try {
        await registerIcons(map);
        if (cancelled) return;

        if (!map.getSource('incidents')) {
          map.addSource('incidents', {
            type: 'geojson',
            data: { type: 'FeatureCollection', features: [] },
            cluster: true,
            clusterRadius: 50,
            clusterMaxZoom: 14,
          });
        }

        if (!map.getLayer('clusters')) {
          map.addLayer({
            id: 'clusters',
            type: 'circle',
            source: 'incidents',
            filter: ['has', 'point_count'],
            paint: {
              'circle-color': [
                'step', ['get', 'point_count'],
                '#2563eb', 10, '#7c3aed', 25, '#dc2626',
              ],
              'circle-radius': [
                'step', ['get', 'point_count'],
                18, 10, 24, 25, 32,
              ],
              'circle-stroke-width': 2,
              'circle-stroke-color': '#ffffff',
              'circle-opacity': 0.9,
            },
          } as CircleLayerSpecification);
        }

        if (!map.getLayer('cluster-count')) {
          map.addLayer({
            id: 'cluster-count',
            type: 'symbol',
            source: 'incidents',
            filter: ['has', 'point_count'],
            layout: {
              'text-field': '{point_count_abbreviated}',
              'text-font': ['Noto Sans Regular'],
              'text-size': 13,
            },
            paint: {
              'text-color': '#ffffff',
            },
          } as SymbolLayerSpecification);
        }

        // Fallback circle for missing icons
        if (!map.getLayer('unclustered-fallback')) {
          map.addLayer({
            id: 'unclustered-fallback',
            type: 'circle',
            source: 'incidents',
            filter: ['!', ['has', 'point_count']],
            paint: {
              'circle-color': [
                'match', ['get', 'status'],
                'open', '#ef4444',
                'closed', '#22c55e',
                '#6b7280',
              ],
              'circle-radius': 10,
              'circle-stroke-width': 2,
              'circle-stroke-color': '#ffffff',
            },
          } as CircleLayerSpecification);
        }

        if (!map.getLayer('unclustered-point')) {
          map.addLayer({
            id: 'unclustered-point',
            type: 'symbol',
            source: 'incidents',
            filter: ['!', ['has', 'point_count']],
            layout: {
              'icon-image': ['get', 'iconImage'],
              'icon-size': 1,
              'icon-allow-overlap': true,
              'icon-ignore-placement': true,
            },
          } as SymbolLayerSpecification);
        }

        // Cluster click -> zoom
        map.on('click', 'clusters', async (e) => {
          const features = map.queryRenderedFeatures(e.point, { layers: ['clusters'] });
          const clusterId = features[0]?.properties?.cluster_id;
          const source = map.getSource('incidents') as GeoJSONSource | undefined;
          if (!source || clusterId == null) return;
          try {
            const zoom = await source.getClusterExpansionZoom(clusterId);
            const geom = features[0].geometry;
            if (geom.type === 'Point') {
              map.easeTo({ center: geom.coordinates as LngLatLike, zoom });
            }
          } catch (err) {
            console.warn('[Map] Failed to expand cluster', err);
          }
        });

        // Unclustered point click -> popup
        const handlePointClick = (e: any) => {
          const feature = e.features?.[0];
          if (!feature) return;
          const props = feature.properties as IncidentFeatureProperties;
          const coords = (feature.geometry as { type: string; coordinates: [number, number] }).coordinates.slice() as [number, number];
          onIncidentSelect?.({
            id: String(props.id),
            title: String(props.title ?? ''),
            description: String(props.description ?? ''),
            category: String(props.category) as Category,
            status: String(props.status) as Status,
            report_count: Number(props.report_count ?? 0),
            created_at: String(props.created_at ?? ''),
            latitude: Number(props.latitude ?? coords[1]),
            longitude: Number(props.longitude ?? coords[0]),
          });

          popupRef.current?.remove();
          const popup = new Popup({ closeButton: true, closeOnClick: true, maxWidth: '320px' })
            .setLngLat(coords)
            .setHTML(renderPopupHtml(props))
            .addTo(map);
          popupRef.current = popup;
        };

        map.on('click', 'unclustered-point', handlePointClick);
        map.on('click', 'unclustered-fallback', handlePointClick);

        map.on('mouseenter', 'clusters', () => { map.getCanvas().style.cursor = 'pointer'; });
        map.on('mouseleave', 'clusters', () => { map.getCanvas().style.cursor = ''; });
        map.on('mouseenter', 'unclustered-point', () => { map.getCanvas().style.cursor = 'pointer'; });
        map.on('mouseleave', 'unclustered-point', () => { map.getCanvas().style.cursor = ''; });
        map.on('mouseenter', 'unclustered-fallback', () => { map.getCanvas().style.cursor = 'pointer'; });
        map.on('mouseleave', 'unclustered-fallback', () => { map.getCanvas().style.cursor = ''; });

        loadedRef.current = true;
        setMapReady(true);
        if (!initialLocateAttemptedRef.current) {
          initialLocateAttemptedRef.current = true;
          locateUser(true);
        }
      } catch (err) {
        console.error('[Map] Initialization error', err);
        setMapError('Failed to initialize the map.');
      }
    });

    return () => {
      cancelled = true;
      popupRef.current?.remove();
      map.remove();
      mapRef.current = null;
      loadedRef.current = false;
      iconsRegisteredRef.current = false;
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Update data when filters/incidents change
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapReady) return;
    const source = map.getSource('incidents') as GeoJSONSource | undefined;
    if (source) {
      source.setData(filteredData as any);
    }
  }, [filteredData, mapReady]);

  // Zoom to selected incident
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapReady || !selectedIncidentId) return;
    const incident = incidents.find((i) => i.id === selectedIncidentId);
    if (incident && isValidCoord(incident.latitude, incident.longitude)) {
      map.easeTo({ center: [incident.longitude, incident.latitude], zoom: Math.max(map.getZoom(), 15) });
    }
  }, [selectedIncidentId, incidents, mapReady]);

  return (
    <div className="relative w-full h-full min-h-[400px]">
      <div ref={containerRef} className="absolute inset-0" />
      <button
        type="button"
        onClick={() => locateUser(false)}
        disabled={!mapReady || locating}
        className="absolute top-3 right-14 z-10 inline-flex items-center justify-center w-9 h-9 rounded-md bg-white text-gray-700 border border-gray-300 shadow hover:bg-gray-50 disabled:opacity-60 disabled:cursor-not-allowed"
        aria-label="Locate me"
        title="Locate me"
      >
        <LocateFixed size={18} className={locating ? 'animate-pulse' : ''} />
      </button>
      {mapError && (
        <div className="absolute inset-0 flex items-center justify-center bg-gray-950/80 z-10">
          <div className="text-center p-6">
            <p className="text-red-400 mb-2">{mapError}</p>
            <p className="text-sm text-gray-400">Check your connection and refresh the page.</p>
          </div>
        </div>
      )}
      {!mapReady && !mapError && (
        <div className="absolute inset-0 flex items-center justify-center bg-gray-950/60 z-10">
          <div className="text-gray-300 text-sm">Loading map…</div>
        </div>
      )}
    </div>
  );
}

function escapeHtml(str: string): string {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function hasValidCoords(lat: number, lng: number): boolean {
  return Number.isFinite(lat) && Number.isFinite(lng) && lat >= -90 && lat <= 90 && lng >= -180 && lng <= 180;
}

function googleMapsUrl(lat: number, lng: number): string {
  return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(lat)},${encodeURIComponent(lng)}`;
}

function renderPopupHtml(props: IncidentFeatureProperties): string {
  const category = CATEGORY_LABELS[props.category as Category] ?? props.category;
  const status = STATUS_COLORS[props.status as Status]?.label ?? props.status;
  const statusColor = props.status === 'open' ? '#ef4444' : '#22c55e';
  const desc = String(props.description || '').slice(0, 160);
  const title = String(props.title || 'Untitled incident');
  const reportCount = Number(props.report_count ?? 0);
  const id = String(props.id ?? '');
  const safeId = escapeHtml(id);
  const lat = Number(props.latitude);
  const lng = Number(props.longitude);
  const coordsValid = hasValidCoords(lat, lng);
  const mapsButton = coordsValid
    ? `<a href="${escapeHtml(googleMapsUrl(lat, lng))}" target="_blank" rel="noopener noreferrer" style="display:inline-flex;align-items:center;justify-content:center;padding:8px 10px;border-radius:8px;background:#2563eb;color:#ffffff;text-decoration:none;font-size:12px;font-weight:600;line-height:1;">Open in Google Maps</a>`
    : `<span style="display:inline-flex;align-items:center;justify-content:center;padding:8px 10px;border-radius:8px;background:#e5e7eb;color:#6b7280;font-size:12px;font-weight:600;line-height:1;cursor:not-allowed;" aria-disabled="true">Open in Google Maps</span>`;

  return `
    <div style="font-family:system-ui,-apple-system,sans-serif;color:#111827;max-width:300px;">
      <div style="font-weight:600;font-size:14px;margin-bottom:6px;line-height:1.35;">${escapeHtml(title)}</div>
      <div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:10px;">
        <span style="font-size:11px;padding:2px 8px;border-radius:9999px;background:#e5e7eb;color:#374151;">${escapeHtml(category)}</span>
        <span style="font-size:11px;padding:2px 8px;border-radius:9999px;background:${statusColor}22;color:${statusColor};font-weight:600;">${escapeHtml(status)}</span>
      </div>
      <div style="font-size:12px;color:#374151;margin-bottom:10px;line-height:1.45;">
        <div style="margin-bottom:4px;"><strong style="color:#111827;">Incident ID:</strong> <span style="font-family:ui-monospace,SFMono-Regular,monospace;font-size:11px;">${safeId}</span></div>
        <div style="margin-bottom:4px;"><strong style="color:#111827;">Category:</strong> ${escapeHtml(category)}</div>
        <div style="margin-bottom:4px;"><strong style="color:#111827;">Status:</strong> ${escapeHtml(status)}</div>
        <div style="margin-bottom:4px;"><strong style="color:#111827;">Reports:</strong> ${reportCount}</div>
        <div><strong style="color:#111827;">Description:</strong> ${escapeHtml(desc)}${String(props.description || '').length > 160 ? '…' : ''}</div>
      </div>
      <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;">
        ${mapsButton}
        <a href="/incidents/${safeId}" style="display:inline-flex;align-items:center;font-size:12px;color:#2563eb;text-decoration:none;font-weight:500;">View incident details →</a>
      </div>
    </div>
  `;
}
