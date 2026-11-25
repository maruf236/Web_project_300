// Owner: Ali. Pure functions (no React, no browser) so they can be unit-tested.
// The BACKEND recalculates length and fare; these numbers are only a preview for the user.
export const BD_BOUNDS = { minLon: 88, maxLon: 93, minLat: 20.5, maxLat: 26.7 }  // same box the API accepts
export const BASE_RATE_BDT_PER_KM = 10                                              // FR-030
export const MAX_ROUTE_POINTS = 4000                                                // API limit is 5000

export function isInsideBangladesh([lon, lat]) {
  return lon >= BD_BOUNDS.minLon && lon <= BD_BOUNDS.maxLon && lat >= BD_BOUNDS.minLat && lat <= BD_BOUNDS.maxLat
}

export function haversineKm([lon1, lat1], [lon2, lat2]) {
  const R = 6371.0088
  const rad = (d) => (d * Math.PI) / 180
  const dLat = rad(lat2 - lat1)
  const dLon = rad(lon2 - lon1)
  const a = Math.sin(dLat / 2) ** 2 + Math.cos(rad(lat1)) * Math.cos(rad(lat2)) * Math.sin(dLon / 2) ** 2
  return 2 * R * Math.asin(Math.sqrt(a))
}

export function pathLengthKm(coords) {
  let km = 0
  for (let i = 1; i < coords.length; i++) km += haversineKm(coords[i - 1], coords[i])
  return km
}

// Base fare = BDT 10 x km. A provider may charge this, less, or zero (FR-030, FR-031).
export function estimateBaseFare(km) {
  return Math.round(km * BASE_RATE_BDT_PER_KM * 100) / 100
}

export function validateRoute(coords) {
  if (!Array.isArray(coords) || coords.length < 2) return { ok: false, error: 'Pick at least two points.' }
  if (coords.some((p) => !Array.isArray(p) || p.length !== 2 || !p.every(Number.isFinite))) return { ok: false, error: 'Route contains an invalid point.' }
  if (!coords.every(isInsideBangladesh)) return { ok: false, error: 'Every point must be inside Bangladesh.' }
  if (pathLengthKm(coords) <= 0) return { ok: false, error: 'The route has no length.' }
  return { ok: true }
}

// Keeps first and last point, samples evenly in between, so the API never receives too many points.
export function thinCoordinates(coords, max = MAX_ROUTE_POINTS) {
  if (coords.length <= max) return coords
  const out = [coords[0]]
  const step = (coords.length - 1) / (max - 1)
  for (let i = 1; i < max - 1; i++) out.push(coords[Math.round(i * step)])
  out.push(coords[coords.length - 1])
  return out
}

// Exactly what POST /api/offers (route) and POST /api/rides/search (route) expect.
export const toLineString = (coords) => ({ type: 'LineString', coordinates: coords })
