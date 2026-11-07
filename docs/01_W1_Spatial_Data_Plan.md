# Week 1 — Spatial Data Planning (Owner: Ali Ahsan Maruf)
Covers FR-012, FR-017..FR-025, UC-009, AT-05..AT-08.

## Data model
- Provider route = PostGIS `LineString`, SRID 4326, snapped to roads by the routing service. Stored on `ride_offers.route_geom`, versioned in `ride_route_versions` (FR-025).
- Student request = pickup point + drop point + requested route LineString (from routing service).
- Length/fare distance: `ST_Length(geom::geography)/1000`.

## Rules -> spatial operations
| Rule | Approach |
|---|---|
| FR-017 1 km ROAD distance | Routing service (OSRM/GraphHopper, Bangladesh extract) provider->pickup; visible only if `>= 1000 m`. Never fall back to `ST_Distance` (FR-019): on routing failure, hide the offer. |
| FR-020 student route 100% inside provider route | Student route snapped to same road graph; `ST_Covers(ST_Buffer(provider::geography, 15)::geometry, student)` (15 m tolerance PROPOSED). No partial pass. |
| FR-021 provider match >= 80% | `ST_Length(ST_Intersection(provider_buffer, student)) / ST_Length(provider)`. **Denominator OPEN (OR-01)**; proposal: provider route length. Compare as integer basis points (AT-08: 79.99 fail / 80.00 pass). |
| FR-024 invalid geometry | `ST_IsValid`, >=2 points, length>0, else reject at publish and match. |
| FR-022 both pass | one SQL predicate; decision logged. |

## Indexes
GiST on `route_geom`; B-tree on (`service_on`, `departure_at`); partial index on available offers.

## Edge-case tests (AT-05..08)
Service OFF hidden; 0.99 vs 1.00 km; route B-C-X vs A-B-C-D-E rejected; empty/self-intersecting geometry rejected.
