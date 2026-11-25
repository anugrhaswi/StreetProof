import { useCallback, useState } from 'react';

interface GeolocationResult {
  lat: number;
  lng: number;
}

export function useGeolocation() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const getCurrentPosition = useCallback(async (): Promise<GeolocationResult> => {
    if (!navigator.geolocation) {
      const msg = 'Geolocation is not supported by your browser.';
      setError(msg);
      throw new Error(msg);
    }

    setIsLoading(true);
    setError(null);

    try {
      const pos = await new Promise<GeolocationPosition>((resolve, reject) => {
        navigator.geolocation.getCurrentPosition(resolve, reject, {
          enableHighAccuracy: true,
          timeout: 10000,
          maximumAge: 0,
        });
      });
      return { lat: pos.coords.latitude, lng: pos.coords.longitude };
    } catch (err) {
      let msg = 'Unable to retrieve your location.';
      if (err && typeof err === 'object' && 'code' in err) {
        const code = (err as GeolocationPositionError).code;
        if (code === 1) msg = 'Location permission denied. You can still select a location manually on the map.';
        else if (code === 2) msg = 'Location unavailable. Please select a location manually on the map.';
        else if (code === 3) msg = 'Location request timed out. Please try again or select manually.';
      }
      setError(msg);
      throw new Error(msg);
    } finally {
      setIsLoading(false);
    }
  }, []);

  return { getCurrentPosition, isLoading, error, clearError: () => setError(null) };
}
