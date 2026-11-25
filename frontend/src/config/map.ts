export const MAP_CONFIG = {
  defaultLat: Number(import.meta.env.VITE_MAP_DEFAULT_LAT ?? '26.7271'),
  defaultLng: Number(import.meta.env.VITE_MAP_DEFAULT_LNG ?? '88.3953'),
  defaultZoom: 15,
  tileStyleUrl: import.meta.env.VITE_MAP_STYLE_URL ?? 'https://tiles.openfreemap.org/styles/liberty',
  photonSearchUrl: 'https://photon.komoot.io/api/',
  photonReverseUrl: 'https://photon.komoot.io/reverse',
  countryCode: 'in',
} as const;
