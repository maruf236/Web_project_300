// Owner: Ali. Snaps clicked points to real roads with an OSRM server.
// If routing fails we return an error. We never draw a straight line instead (FR-019 spirit).
const OSRM = (import.meta.env?.VITE_OSRM_URL || 'https://router.project-osrm.org').replace(/\/$/, '')
export const MAX_WAYPOINTS = 25

export class RoutingError extends Error {}

export async function snapToRoad(waypoints, signal) {
  if (waypoints.length < 2) throw new RoutingError('Pick at least two points.')
  if (waypoints.length > MAX_WAYPOINTS) throw new RoutingError(`Use at most ${MAX_WAYPOINTS} points.`)
  const path = waypoints.map(([lon, lat]) => `${lon.toFixed(6)},${lat.toFixed(6)}`).join(';')
  let res
  try {
    res = await fetch(`${OSRM}/route/v1/driving/${path}?overview=full&geometries=geojson&steps=false`, { signal })
  } catch (e) {
    if (e?.name === 'AbortError') throw e
    throw new RoutingError('The routing service is not reachable. Check your internet connection.')
  }
  if (!res.ok) throw new RoutingError('The routing service returned an error. Try again.')
  const data = await res.json()
  if (data.code !== 'Ok' || !data.routes?.length) throw new RoutingError('No road route was found between these points.')
  const r = data.routes[0]
  return { coordinates: r.geometry.coordinates, distanceKm: r.distance / 1000 }
}
