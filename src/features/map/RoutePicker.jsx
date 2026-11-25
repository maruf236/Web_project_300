// Owner: Ali. Click the map to add points; the route is snapped to roads and returned as GeoJSON.
// onChange({ route, distanceKm, waypoints }) is called with route = null until a valid route exists.
import { useEffect, useRef, useState } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { Alert, Button, TextField } from '../../shared/ui/index.js'
import { BD_BOUNDS, isInsideBangladesh, thinCoordinates, toLineString, validateRoute } from './routeUtils.js'
import { MAX_WAYPOINTS, RoutingError, snapToRoad } from './osrm.js'

const DHAKA = [23.78, 90.4] // [lat, lon] for Leaflet

export default function RoutePicker({ onChange, height = 420 }) {
  const mapEl = useRef(null)
  const mapRef = useRef(null)
  const pointsLayer = useRef(null)
  const routeLayer = useRef(null)
  const onChangeRef = useRef(onChange)
  onChangeRef.current = onChange

  const [waypoints, setWaypoints] = useState([]) // [lon, lat]
  const [status, setStatus] = useState('idle')   // idle | snapping | ok | error
  const [message, setMessage] = useState('')
  const [manual, setManual] = useState('')

  const addPoint = (p) => {
    if (!isInsideBangladesh(p)) { setStatus('error'); setMessage('That point is outside Bangladesh.'); return }
    setWaypoints((w) => {
      if (w.length >= MAX_WAYPOINTS) { setStatus('error'); setMessage(`You can use at most ${MAX_WAYPOINTS} points.`); return w }
      return [...w, p]
    })
  }

  // create the map once
  useEffect(() => {
    if (mapRef.current) return
    const bounds = L.latLngBounds([BD_BOUNDS.minLat, BD_BOUNDS.minLon], [BD_BOUNDS.maxLat, BD_BOUNDS.maxLon])
    const map = L.map(mapEl.current, { center: DHAKA, zoom: 11, minZoom: 6, maxBounds: bounds, maxBoundsViscosity: 1 })
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19, attribution: '&copy; OpenStreetMap contributors' }).addTo(map)
    pointsLayer.current = L.layerGroup().addTo(map)
    routeLayer.current = L.layerGroup().addTo(map)
    map.on('click', (e) => addPoint([e.latlng.lng, e.latlng.lat]))
    mapRef.current = map
    return () => { map.remove(); mapRef.current = null }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // redraw markers, then snap to roads when there are 2+ points
  useEffect(() => {
    if (!mapRef.current) return
    pointsLayer.current.clearLayers()
    routeLayer.current.clearLayers()
    waypoints.forEach(([lon, lat], i) => {
      L.circleMarker([lat, lon], { radius: 8, color: i === 0 ? '#2E7D32' : i === waypoints.length - 1 ? '#C62828' : '#1F3A5F', fillOpacity: 0.9 })
        .bindTooltip(i === 0 ? 'Start' : i === waypoints.length - 1 ? 'End' : `Via ${i}`).addTo(pointsLayer.current)
    })
    if (waypoints.length < 2) {
      setStatus('idle'); setMessage('')
      onChangeRef.current?.({ route: null, distanceKm: 0, waypoints })
      return
    }
    const ctl = new AbortController()
    setStatus('snapping'); setMessage('')
    const t = setTimeout(async () => {
      try {
        const { coordinates, distanceKm } = await snapToRoad(waypoints, ctl.signal)
        const coords = thinCoordinates(coordinates)
        const check = validateRoute(coords)
        if (!check.ok) throw new RoutingError(check.error)
        L.polyline(coords.map(([lon, lat]) => [lat, lon]), { color: '#2A7F8E', weight: 5 }).addTo(routeLayer.current)
        mapRef.current.fitBounds(routeLayer.current.getLayers()[0].getBounds(), { padding: [30, 30] })
        setStatus('ok'); setMessage('')
        onChangeRef.current?.({ route: toLineString(coords), distanceKm, waypoints })
      } catch (e) {
        if (e?.name === 'AbortError') return
        setStatus('error'); setMessage(e instanceof RoutingError ? e.message : 'Could not build the route.')
        onChangeRef.current?.({ route: null, distanceKm: 0, waypoints })
      }
    }, 400)
    return () => { clearTimeout(t); ctl.abort() }
  }, [waypoints])

  function addManual(ev) {
    ev.preventDefault()
    const m = manual.split(/[,\s]+/).filter(Boolean).map(Number)
    if (m.length !== 2 || !m.every(Number.isFinite)) { setStatus('error'); setMessage('Type latitude and longitude, for example: 23.7461, 90.3742'); return }
    addPoint([m[1], m[0]])
    setManual('')
  }

  return (
    <div>
      <div ref={mapEl} style={{ height }} className="w-full rounded-md border border-slate-300" role="application" aria-label="Map. Click to add route points, or type coordinates below." />
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <Button variant="secondary" onClick={() => setWaypoints((w) => w.slice(0, -1))} disabled={!waypoints.length}>Undo last point</Button>
        <Button variant="ghost" onClick={() => setWaypoints([])} disabled={!waypoints.length}>Clear route</Button>
        <span className="text-sm text-slate-600" aria-live="polite">
          {status === 'snapping' ? 'Finding the road route...' : `${waypoints.length} point${waypoints.length === 1 ? '' : 's'} selected`}
        </span>
      </div>
      <form onSubmit={addManual} className="mt-3 flex items-end gap-2">
        <div className="flex-1"><TextField label="Add a point by coordinates (keyboard alternative)" value={manual} onChange={(e) => setManual(e.target.value)} placeholder="latitude, longitude" /></div>
        <Button type="submit" variant="secondary" className="mb-4">Add point</Button>
      </form>
      {status === 'error' && <Alert variant="error">{message}</Alert>}
    </div>
  )
}
