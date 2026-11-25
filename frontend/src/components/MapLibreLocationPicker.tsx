/// <reference types='maplibre-gl' />
import { useEffect, useRef, useState, useCallback } from 'react';
import { AttributionControl, Map as MapLibreMap, setWorkerUrl, type LngLatLike, type AttributionControlOptions, type ControlPosition } from 'maplibre-gl';
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url';
import {
  Crosshair,
  Loader2,
  LocateFixed,
  MapPin,
  Search,
  X,
} from 'lucide-react';
import { MAP_CONFIG } from '../config/map';
import { useGeolocation } from '../hooks/useGeolocation';
import { useToast } from './Toast';

// Register MapLibre worker once at module level
setWorkerUrl(workerUrl);

interface LocationPickerProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (lat: number, lng: number) => void;
  initialLat?: number;
  initialLng?: number;
  autoLocateOnOpen?: boolean;
}

interface Center {
  lat: number;
  lng: number;
}

interface SelectedLocation {
  lat: number;
  lng: number;
  formattedAddress?: string;
  addressComponents?: PhotonFeature['properties'];
  isGeocoding: boolean;
}

interface PhotonFeature {
  type: 'Feature';
  geometry: {
    type: 'Point';
    coordinates: [number, number];
  };
  properties: {
    name: string;
    housenumber?: string;
    street?: string;
    city?: string;
    state?: string;
    country?: string;
    postcode?: string;
    type?: string;
    osm_type?: string;
    osm_id?: number;
    extent?: number[];
    countrycode?: string;
    district?: string;
    county?: string;
    suburb?: string;
    village?: string;
    hamlet?: string;
    locality?: string;
    formatted: string;
    [key: string]: unknown;
  };
}

interface PhotonResponse {
  type: 'FeatureCollection';
  features: PhotonFeature[];
}

const DEFAULT_CENTER: Center = { lat: MAP_CONFIG.defaultLat, lng: MAP_CONFIG.defaultLng };
const DEFAULT_ZOOM = MAP_CONFIG.defaultZoom;

function getStr(props: PhotonFeature['properties'], key: string): string {
  const val = props[key];
  return (val as string) || '';
}

function formatPhotonAddress(props: PhotonFeature['properties']): string {
  const parts: string[] = [];
  const name = getStr(props, 'name');
  if (name) parts.push(name);
  const housenumber = getStr(props, 'housenumber');
  const street = getStr(props, 'street');
  if (housenumber && street) parts.push(housenumber + ' ' + street);
  else if (street) parts.push(street);
  const city = getStr(props, 'city');
  const town = getStr(props, 'town');
  const village = getStr(props, 'village');
  const suburb = getStr(props, 'suburb');
  const locality = getStr(props, 'locality');
  if (city || town || village || suburb || locality) {
    parts.push(city || town || village || suburb || locality);
  }
  const state = getStr(props, 'state');
  if (state) parts.push(state);
  const country = getStr(props, 'country');
  if (country) parts.push(country);
  const formatted = getStr(props, 'formatted');
  return parts.filter(Boolean).join(', ') || formatted || 'Selected map location';
}

function extractLocalityCityState(props: PhotonFeature['properties']): string {
  const parts: string[] = [];
  const suburb = getStr(props, 'suburb');
  const locality = getStr(props, 'locality');
  const city = getStr(props, 'city');
  const town = getStr(props, 'town');
  const village = getStr(props, 'village');
  if (suburb || locality || city || town || village) {
    parts.push(suburb || locality || city || town || village);
  }
  const state = getStr(props, 'state');
  if (state) parts.push(state);
  const country = getStr(props, 'country');
  if (country) parts.push(country.toUpperCase());
  return parts.filter(Boolean).join(', ');
}

export default function MapLibreLocationPicker({
  isOpen,
  onClose,
  onConfirm,
  initialLat,
  initialLng,
  autoLocateOnOpen = true,
}: LocationPickerProps) {
  const toast = useToast();
  const { getCurrentPosition, isLoading: geoLoading } = useGeolocation();
  const hasInitial =
    typeof initialLat === 'number' &&
    typeof initialLng === 'number' &&
    Number.isFinite(initialLat) &&
    Number.isFinite(initialLng);

  const mapRef = useRef<HTMLDivElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const triggerRef = useRef<HTMLElement>(null);
  const map = useRef<MapLibreMap | null>(null);
  const idleTimer = useRef<number | null>(null);
  const moveendListener = useRef<() => void | null>(null);
  const lastGeocodedKey = useRef<string>('');
  const searchAbortController = useRef<AbortController | null>(null);
  const searchCache = useRef<Map<string, PhotonFeature[]>>(new Map());
  const pendingSearchQuery = useRef<string>('');
  const mountedRef = useRef(true);

  const [selectedLocation, setSelectedLocation] = useState<SelectedLocation>({
    lat: hasInitial ? initialLat! : DEFAULT_CENTER.lat,
    lng: hasInitial ? initialLng! : DEFAULT_CENTER.lng,
    formattedAddress: undefined,
    addressComponents: undefined,
    isGeocoding: false,
  });
  const [mapLoading, setMapLoading] = useState(true);
  const [mapError, setMapError] = useState<string | null>(null);
  const [searchResults, setSearchResults] = useState<PhotonFeature[]>([]);
  const [showSearchResults, setShowSearchResults] = useState(false);
  const [searching, setSearching] = useState(false);
  const [selectedResultIndex, setSelectedResultIndex] = useState(-1);
  const [searchQuery, setSearchQuery] = useState('');

  // Focus management
  useEffect(() => {
    if (isOpen) {
      triggerRef.current = document.activeElement as HTMLElement;
      const frame = requestAnimationFrame(() => searchInputRef.current?.focus());
      return () => cancelAnimationFrame(frame);
    } else if (triggerRef.current) {
      triggerRef.current.focus();
    }
  }, [isOpen]);

  // Trap focus in modal
  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        onClose();
      }
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  // Initialize MapLibre map
  useEffect(() => {
    if (!isOpen) return;

    mountedRef.current = true;
    const initMap = async () => {
      try {
        setMapLoading(true);
        setMapError(null);

        if (!mountedRef.current || !mapRef.current) return;

        const initialCenter: LngLatLike = hasInitial
          ? [initialLng!, initialLat!]
          : [DEFAULT_CENTER.lng, DEFAULT_CENTER.lat];

        const attributionOptions: AttributionControlOptions = { compact: true };

        map.current = new MapLibreMap({
          container: mapRef.current,
          style: MAP_CONFIG.tileStyleUrl,
          center: initialCenter,
          zoom: DEFAULT_ZOOM,
          attributionControl: attributionOptions,
          cooperativeGestures: true,
        });

        map.current?.addControl(new AttributionControl(attributionOptions), 'bottom-right' as ControlPosition);

        // Reverse geocode initial position
        if (hasInitial) {
          reverseGeocode(initialLat!, initialLng!);
        }

        // Moveend listener for reverse geocoding (MapLibre uses moveend, not idle)
        const listener = () => {
          if (!mountedRef.current) return;
          const center = map.current?.getCenter();
          if (!center) return;
          const coordKey = center.lat.toFixed(6) + ',' + center.lng.toFixed(6);
          if (coordKey === lastGeocodedKey.current) return;
          if (idleTimer.current) window.clearTimeout(idleTimer.current);
          idleTimer.current = window.setTimeout(() => reverseGeocode(center.lat, center.lng), 500);
        };
        moveendListener.current = listener;
        map.current?.on('moveend', listener);

        setMapLoading(false);
      } catch (err) {
        if (!mountedRef.current) return;
        setMapError(err instanceof Error ? err.message : 'Failed to load map');
        setMapLoading(false);
      }
    };

    initMap();

    return () => {
      mountedRef.current = false;
      if (idleTimer.current) window.clearTimeout(idleTimer.current);
      if (map.current && moveendListener.current) {
        map.current.off('moveend', moveendListener.current);
      }
      if (map.current) {
        map.current.remove();
        map.current = null;
      }
    };
  }, [isOpen, hasInitial, initialLat, initialLng]);

  // Search with Photon API
  const performSearch = useCallback(async (query: string) => {
    if (query.length < 3) {
      setSearchResults([]);
      setShowSearchResults(false);
      return;
    }

    // Check cache first
    if (searchCache.current.has(query)) {
      setSearchResults(searchCache.current.get(query)!);
      setShowSearchResults(true);
      return;
    }

    // Cancel previous request
    if (searchAbortController.current) {
      searchAbortController.current.abort();
    }
    searchAbortController.current = new AbortController();
    const signal = searchAbortController.current.signal;

    setSearching(true);
    pendingSearchQuery.current = query;

    try {
      const center = map.current?.getCenter();
      const params = new URLSearchParams({
        q: query,
        limit: '5',
        lang: 'en',
        countrycode: MAP_CONFIG.countryCode,
      });

      // Bias towards current map center if available
      if (center) {
        params.set('lat', center.lat.toString());
        params.set('lon', center.lng.toString());
        params.set('location_bias_scale', '0.4');
      }

      const response = await fetch(MAP_CONFIG.photonSearchUrl + '?' + params, { signal });
      if (!response.ok) throw new Error('Search request failed');

      const data: PhotonResponse = await response.json();
      const features = data.features || [];

      if (!mountedRef.current) return;
      if (pendingSearchQuery.current !== query) return; // Stale request

      searchCache.current.set(query, features);
      setSearchResults(features);
      setShowSearchResults(true);
      setSelectedResultIndex(-1);
    } catch (err) {
      if (err instanceof Error && err.name === 'AbortError') return;
      console.error('Photon search error:', err);
      if (!mountedRef.current) return;
      setSearchResults([]);
    } finally {
      if (mountedRef.current) setSearching(false);
    }
  }, []);

  // Debounced search handler
  const searchTimeout = useRef<number | null>(null);
  const handleSearchInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setSearchQuery(value);
    const query = value.trim();
    pendingSearchQuery.current = query;
    if (searchTimeout.current) window.clearTimeout(searchTimeout.current);
    if (query.length < 3) {
      setSearchResults([]);
      setShowSearchResults(false);
      return;
    }
    searchTimeout.current = window.setTimeout(() => performSearch(query), 500);
  };

  // Handle keyboard navigation in search results
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!showSearchResults || searchResults.length === 0) return;

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setSelectedResultIndex((prev) => Math.min(prev + 1, searchResults.length - 1));
        break;
      case 'ArrowUp':
        e.preventDefault();
        setSelectedResultIndex((prev) => Math.max(prev - 1, -1));
        break;
      case 'Enter':
        e.preventDefault();
        if (selectedResultIndex >= 0) {
          selectSearchResult(searchResults[selectedResultIndex]);
        }
        break;
      case 'Escape':
        setShowSearchResults(false);
        setSelectedResultIndex(-1);
        break;
    }
  };

  const selectSearchResult = (feature: PhotonFeature) => {
    const [lng, lat] = feature.geometry.coordinates;
    if (!map.current) return;

    map.current.flyTo({ center: [lng, lat] as LngLatLike, zoom: 17, duration: 500 });
    setSelectedLocation({
      lat,
      lng,
      formattedAddress: feature.properties.formatted || formatPhotonAddress(feature.properties),
      addressComponents: feature.properties,
      isGeocoding: false,
    });
    setSearchResults([]);
    setShowSearchResults(false);
    setSelectedResultIndex(-1);
    setSearchQuery(feature.properties.formatted || formatPhotonAddress(feature.properties));
    pendingSearchQuery.current = '';
    searchInputRef.current?.blur();
  };

  // Reverse geocoding with Photon
  const reverseGeocode = async (lat: number, lng: number) => {
    const coordKey = lat.toFixed(6) + ',' + lng.toFixed(6);
    if (coordKey === lastGeocodedKey.current) return;

    setSelectedLocation((prev) => ({ ...prev, isGeocoding: true }));

    try {
      const params = new URLSearchParams({
        lat: lat.toString(),
        lon: lng.toString(),
        lang: 'en',
      });

      const response = await fetch(MAP_CONFIG.photonReverseUrl + '?' + params);
      if (!response.ok) throw new Error('Reverse geocode failed');

      const data: PhotonResponse = await response.json();
      const feature = data.features?.[0];

      if (!mountedRef.current) return;

      if (feature) {
        lastGeocodedKey.current = coordKey;
        setSelectedLocation({
          lat,
          lng,
          formattedAddress: feature.properties.formatted || formatPhotonAddress(feature.properties),
          addressComponents: feature.properties,
          isGeocoding: false,
        });
      } else {
        setSelectedLocation((prev) => ({ ...prev, isGeocoding: false }));
      }
    } catch (err) {
      console.error('Photon reverse geocode error:', err);
      if (!mountedRef.current) return;
      setSelectedLocation((prev) => ({ ...prev, isGeocoding: false }));
    }
  };

  const handleUseMyLocation = async () => {
    try {
      const pos = await getCurrentPosition();
      if (!map.current) return;
      map.current.flyTo({ center: [pos.lng, pos.lat] as LngLatLike, zoom: 17, duration: 500 });
      // Reverse geocode will fire on moveend
      toast.success('Map centered on your current location. Adjust if needed, then confirm.');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Unable to retrieve your location.');
    }
  };

  const handleConfirm = () => {
    onConfirm(selectedLocation.lat, selectedLocation.lng);
  };

  // Auto-locate on open if permission already granted
  useEffect(() => {
    if (!isOpen || hasInitial || !autoLocateOnOpen || mapLoading || !map.current) return;
    navigator.permissions
      ?.query({ name: 'geolocation' })
      .then((status) => {
        if (status.state === 'granted') handleUseMyLocation();
      })
      .catch(() => {});
  }, [isOpen, hasInitial, autoLocateOnOpen, mapLoading]);

  // Click outside search results to close
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (searchInputRef.current && !searchInputRef.current.contains(e.target as Node)) {
        setShowSearchResults(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  if (!isOpen) return null;

  const addressLine = selectedLocation.formattedAddress || 'Selected map location';
  const localityLine = selectedLocation.addressComponents
    ? extractLocalityCityState(selectedLocation.addressComponents)
    : '';

  return (
    <div className='fixed inset-0 z-[60] flex items-end sm:items-center justify-center'>
      <div className='absolute inset-0 bg-black/70' aria-hidden='true' onClick={onClose} />
      <div
        className='relative w-full h-full sm:max-w-3xl sm:h-[min(90vh,720px)] bg-gray-950 sm:border sm:border-gray-800 sm:rounded-xl shadow-2xl flex flex-col overflow-hidden'
        role='dialog'
        aria-modal='true'
        aria-labelledby='picker-title'
      >
        <div className='flex items-center justify-between px-4 sm:px-5 py-3 border-b border-gray-800 bg-gray-950/95 backdrop-blur'>
          <div>
            <h3 id='picker-title' className='text-base sm:text-lg font-semibold text-white'>
              Select issue location
            </h3>
            <p className='text-xs text-gray-400'>
              Search or drag the map to place the pin at the issue location.
            </p>
          </div>
          <button
            onClick={onClose}
            className='p-2 text-gray-400 hover:text-white rounded-md hover:bg-gray-800'
            aria-label='Close location picker'
          >
            <X size={18} />
          </button>
        </div>

        <div className='relative flex-1 min-h-[300px] sm:min-h-0 flex flex-col'>
          {/* Search box */}
          <div className='p-3 sm:p-4 border-b border-gray-800 bg-gray-950/50 backdrop-blur sticky top-0 z-10 relative'>
            <div className='relative'>
              <Search
                className='absolute left-3 top-1/2 -translate-y-1/2 text-gray-500'
                size={18}
              />
              <input
                ref={searchInputRef}
                type='text'
                placeholder='Search address, landmark, or locality...'
                disabled={mapLoading || !map.current}
                value={searchQuery}
                onChange={handleSearchInput}
                onKeyDown={handleKeyDown}
                onFocus={() => searchQuery.trim() && setShowSearchResults(true)}
                className='w-full pl-10 pr-3 py-2.5 rounded-lg bg-gray-900 border border-gray-700 text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-brand-500/40 text-sm disabled:opacity-50'
                aria-label='Search location'
                aria-autocomplete='list'
                aria-controls='search-results'
                aria-expanded={showSearchResults && searchResults.length > 0}
              />
              {searching && (
                <Loader2
                  className='absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 animate-spin'
                  size={16}
                />
              )}
            </div>

            {/* Search results dropdown */}
            {showSearchResults && searchResults.length > 0 && (
              <div
                id='search-results'
                className='absolute top-full left-0 right-0 mt-1 bg-gray-950 border border-gray-700 rounded-lg shadow-xl overflow-hidden z-20 max-h-60 overflow-y-auto'
                role='listbox'
              >
                {searchResults.map((feature, index) => (
                  <button
                    key={feature.properties.osm_type + '-' + feature.properties.osm_id}
                    type='button'
                    onClick={() => selectSearchResult(feature)}
                    onMouseEnter={() => setSelectedResultIndex(index)}
                    className={'w-full px-3 py-2.5 text-left text-sm flex items-center gap-2 ' + (index === selectedResultIndex
                      ? 'bg-brand-500/20 text-white'
                      : 'text-gray-300 hover:bg-gray-800 hover:text-white')}
                    role='option'
                    aria-selected={index === selectedResultIndex}
                  >
                    <MapPin size={16} className='text-brand-400 shrink-0' />
                    <div className='flex-1 min-w-0'>
                      <p className='font-medium truncate'>{feature.properties.name || 'Unnamed location'}</p>
                      <p className='text-xs text-gray-500 truncate'>{formatPhotonAddress(feature.properties)}</p>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Map container */}
          <div className='relative flex-1 min-h-0'>
            <div
              ref={mapRef}
              className='h-full w-full'
              style={{ height: '100%', width: '100%' }}
              aria-hidden='true'
            />

            {mapLoading && (
              <div className='absolute inset-0 bg-gray-950/90 flex items-center justify-center z-20'>
                <div className='text-center'>
                  <Loader2 className='mx-auto mb-2 animate-spin text-brand-400' size={32} />
                  <p className='text-sm text-gray-400'>
                    {mapError ? 'Failed to load map' : 'Loading map...'}
                  </p>
                </div>
              </div>
            )}

            {mapError && !mapLoading && (
              <div className='absolute inset-0 bg-gray-950/90 flex items-center justify-center z-20 p-4'>
                <div className='text-center text-sm text-red-400 max-w-xs'>
                  <p>{mapError}</p>
                  <p className='mt-2 text-xs text-gray-500'>
                    The map could not be loaded. You can still select a location manually.
                  </p>
                </div>
              </div>
            )}

            {/* Fixed center pin */}
            <div className='pointer-events-none absolute inset-0 z-[1000] flex items-center justify-center'>
              <div className='relative -mt-8'>
                <MapPin
                  size={36}
                  className='text-red-500 drop-shadow-[0_2px_4px_rgba(0,0,0,0.8)]'
                  fill='currentColor'
                  strokeWidth={1.5}
                />
                <div className='absolute left-1/2 -bottom-1 w-2 h-2 -translate-x-1/2 rounded-full bg-red-500/50 blur' />
              </div>
            </div>
            <div className='pointer-events-none absolute inset-0 z-[999] flex items-center justify-center'>
              <Crosshair size={20} className='text-white/40' />
            </div>
            <div className='absolute top-3 left-3 z-[1000] rounded-md bg-gray-950/80 border border-gray-700 px-2.5 py-1.5 text-[11px] text-gray-300 backdrop-blur'>
              Map center = selected location
            </div>
          </div>

          {/* Bottom confirmation panel */}
          <div className='border-t border-gray-800 bg-gray-950/95 backdrop-blur p-4 sm:p-5 space-y-4'>
            <div className='text-sm'>
              <p className='text-gray-400'>Selected location</p>
              <p className='text-white font-medium mt-1'>{addressLine}</p>
              {localityLine && (
                <p className='text-xs text-gray-400 mt-1'>{localityLine}</p>
              )}
              {selectedLocation.isGeocoding && (
                <div className='flex items-center gap-2 mt-2 text-xs text-gray-400'>
                  <Loader2 className='animate-spin text-brand-400' size={12} />
                  <span>Updating address...</span>
                </div>
              )}
            </div>
            <div className='flex flex-col sm:flex-row gap-3'>
              <button
                type='button'
                onClick={handleUseMyLocation}
                disabled={geoLoading || mapLoading || !map.current}
                className='inline-flex items-center justify-center gap-2 flex-1 px-3 py-2.5 rounded-lg border border-gray-700 text-gray-200 hover:text-white hover:border-gray-500 disabled:opacity-50 text-sm'
              >
                {geoLoading ? (
                  <Loader2 size={16} className='animate-spin' />
                ) : (
                  <LocateFixed size={16} />
                )}
                {geoLoading ? 'Locating...' : 'Use my location'}
              </button>
              <button
                type='button'
                onClick={onClose}
                className='flex-1 px-4 py-2.5 rounded-lg border border-gray-700 text-gray-300 hover:text-white text-sm'
              >
                Cancel
              </button>
              <button
                type='button'
                onClick={handleConfirm}
                disabled={mapLoading}
                className='flex-1 px-4 py-2.5 rounded-lg bg-brand-500 hover:bg-brand-400 text-white text-sm font-medium disabled:opacity-50'
              >
                Confirm this location
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
