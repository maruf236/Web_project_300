# Frontend Week 1 - Ali (A1, A2)
Folder: `src/features/map`. Library: Leaflet + OpenStreetMap tiles. Road snapping: OSRM.

## A1 Prototype and decisions
- Page `/map-demo` lets you draw a route and shows distance, base-fare estimate and the exact GeoJSON that `POST /api/offers` and `POST /api/rides/search` expect.
- Route data format: GeoJSON `LineString` with `[longitude, latitude]` points, at most 4000 points (backend limit is 5000).
- Points must be inside Bangladesh (same box as the backend: lon 88-93, lat 20.5-26.7); the map cannot be panned outside it.
- Road snapping uses OSRM. If routing fails the screen shows an error. It never draws a straight line instead.
- Public OSRM and OpenStreetMap tile servers are for development only. Production needs a self-hosted OSRM and a proper tile provider (open decision).

## A2 Route picker component
`<RoutePicker onChange={({ route, distanceKm, waypoints }) => ...} height={420} />`
- Click to add start, via points and end (max 25 points). Markers: green start, red end.
- Undo last point, Clear route.
- Keyboard alternative: type `latitude, longitude` and press Add point.
- `route` is `null` until a valid snapped route exists, so a form can simply disable Submit when it is `null`.

## Files
`routeUtils.js` (distance, fare, bounds, thinning; no React), `osrm.js`, `RoutePicker.jsx`, `MapDemoPage.jsx`, `routes.jsx`, `routeUtils.test.js` (7 tests).

## Notes
- Fare shown is an estimate (BDT 10 per km, FR-030). The server calculates the final fare and a provider may charge less or zero.
- Plain `leaflet` is used (not react-leaflet) to avoid version conflicts; markers are circle markers so no image files are needed.

## Next (Week 2)
Service ON/OFF control, location sharing, publish offer form, my offers (A3 to A5).
