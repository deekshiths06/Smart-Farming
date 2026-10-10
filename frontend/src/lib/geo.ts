export type LngLat = [number, number];

const EARTH_RADIUS_M = 6371008.8;

export const SQM_PER = {
  acre: 4046.8564224,
  hectare: 10000,
  square_metre: 1,
} as const;

/** Approximate area of a lon/lat ring (Chamberlain–Duquette). */
export function polygonAreaSquareMetres(ringLonLat: LngLat[]): number {
  if (!ringLonLat || ringLonLat.length < 4) return 0;
  const ring = ringLonLat.map((p) => [p[0], p[1]] as LngLat);
  if (ring[0][0] !== ring[ring.length - 1][0] || ring[0][1] !== ring[ring.length - 1][1]) {
    ring.push([ring[0][0], ring[0][1]]);
  }
  let total = 0;
  for (let i = 0; i < ring.length - 1; i++) {
    const lon1 = (ring[i][0] * Math.PI) / 180;
    const lat1 = (ring[i][1] * Math.PI) / 180;
    const lon2 = (ring[i + 1][0] * Math.PI) / 180;
    const lat2 = (ring[i + 1][1] * Math.PI) / 180;
    let dlon = lon2 - lon1;
    while (dlon > Math.PI) dlon -= 2 * Math.PI;
    while (dlon < -Math.PI) dlon += 2 * Math.PI;
    total += dlon * (2 + Math.sin(lat1) + Math.sin(lat2));
  }
  return Math.abs(total) * EARTH_RADIUS_M * EARTH_RADIUS_M * 0.5;
}

export function formatArea(acres: number): string {
  if (acres >= 10) return acres.toFixed(1);
  if (acres >= 1) return acres.toFixed(2);
  return acres.toFixed(3);
}

export function toCircleLngLat(points: Array<[number, number]>): Array<[number, number]> {
  if (points.length < 3) return points;
  const first = points[0];
  const last = points[points.length - 1];
  if (first[0] === last[0] && first[1] === last[1]) return points;
  return [...points, first];
}

/** Convert a GeoJSON boundary loaded from the backend back into lat/lng pairs. */
export function boundaryToLatLng(boundary: { coordinates: number[][][] }): Array<[number, number]> {
  const ring = boundary?.coordinates?.[0] ?? [];
  return ring.map((position) => [position[1], position[0]] as [number, number]);
}

/** Build GeoJSON (lon/lat) from lat/lng drawing points. */
export function latLngToBoundary(points: Array<[number, number]>): {
  type: "Polygon";
  coordinates: number[][][];
} {
  const ring = points.map((p) => [p[1], p[0]]);
  if (ring[0][0] !== ring[ring.length - 1][0] || ring[0][1] !== ring[ring.length - 1][1]) {
    ring.push([...ring[0]]);
  }
  return { type: "Polygon", coordinates: [ring] };
}