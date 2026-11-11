# Week 4 — Road Routing Engine (Owner: Ali Ahsan Maruf, "Maruf Week 4")
Covers FR-017..FR-025, UC-008, UC-009, AT-05..AT-08.

## Files
- `app/services/matching.py` — pure rules (1 km, 100% containment, 80%), unit-tested
- `app/services/routing.py` — OSRM road-distance client
- `app/routes/search.py` — `POST /api/rides/search`, `POST /api/rides/provider-location`
- `db/migrations/004_maruf_week4.sql` — `provider_locations`, `match_decisions` (also appended to `db/schema.sql`)
- `tests/test_matching.py` — 8 tests (AT-06/07/08, FR-019, FR-024)

## Check order (cheapest first, all must pass: FR-022)
1. Offer is published, has a seat, provider Service ON (AT-05), rider verified, identity verified, not suspended, departs in the window.
2. PostGIS bounding-box prefilter (GiST) then `ST_Covers(15 m corridor around provider route, student route)` = 100% containment (AT-07).
3. Provider-side match in integer basis points, floored; >= 8000 (AT-08).
4. OSRM **road** distance provider -> student pickup >= 1000 m (AT-06). If routing fails the offer is hidden; straight-line distance is never used (FR-019).
Every evaluated offer is written to `match_decisions` (UC-009). Students see only matches, never rejection reasons.

## Assumptions to approve
- **OR-01 (OPEN):** 80% = shared length ÷ provider route length. Change only `provider_match_bps()`.
- 15 m corridor tolerance for road-snapping/GPS error.
- Provider location older than 15 min is not "usable" (FR-018): the offer's planned start point is used instead.
- Student pickup = first point of the requested route.
- Public OSRM demo server is for development only; self-host OSRM with the Bangladesh extract for production.

## Limits (honest)
Matching SQL and OSRM calls were not run against a live database here; only the rule logic is unit-tested. Run `requests_week4.http` after setting up PostgreSQL. Booking (Week 5) must re-check that the offer's `route_version` is unchanged (FR-025).
