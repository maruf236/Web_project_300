"""Ride search + route matching (UC-008, UC-009) and provider location. Owner: Ali (Week 4)."""
import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional
from uuid import UUID
from flask import Blueprint, request, jsonify, g
from pydantic import BaseModel, Field, model_validator
from ..db import tx, fetch_one
from ..errors import HttpError
from ..security import (require_auth, require_contact_verified, require_verified_identity, require_category)
from ..services import matching, routing
from .offers import Route, provider_guard

bp = Blueprint("rides", __name__)
LOCATION_MAX_AGE = timedelta(minutes=15)   # "latest usable" provider location (FR-018). PROPOSED.
MAX_CANDIDATES = 200

class SearchIn(BaseModel):
    route: Route                       # student's requested route; first point = pickup
    depart_after: datetime
    depart_before: datetime
    limit: int = Field(default=20, ge=1, le=50)

    @model_validator(mode="after")
    def _window(self):
        if self.depart_after.tzinfo is None:
            self.depart_after = self.depart_after.replace(tzinfo=timezone.utc)
        if self.depart_before.tzinfo is None:
            self.depart_before = self.depart_before.replace(tzinfo=timezone.utc)
        if not (self.depart_after < self.depart_before <= self.depart_after + timedelta(hours=48)):
            raise ValueError("depart_before must be after depart_after, within 48 hours")
        return self

class LocationIn(BaseModel):
    lon: float = Field(ge=88, le=93)
    lat: float = Field(ge=20.5, le=26.7)

CANDIDATE_SQL = """
WITH s AS (SELECT ST_SetSRID(ST_GeomFromGeoJSON(%(route)s),4326) AS g)
SELECT o.id, o.provider_id, o.origin_name, o.destination_name, o.departure_at, o.window_minutes,
       o.fare_bdt, o.route_length_km, o.route_version, split_part(u.full_name,' ',1) AS provider_first_name,
       ST_X(ST_StartPoint(o.route_geom)) AS start_lon, ST_Y(ST_StartPoint(o.route_geom)) AS start_lat,
       ST_Length(o.route_geom::geography) AS provider_m,
       ST_Covers(ST_Buffer(o.route_geom::geography, %(tol)s)::geometry, s.g) AS covered,
       ST_Length(ST_Intersection(ST_Buffer(o.route_geom::geography, %(tol)s)::geometry, s.g)::geography) AS overlap_m,
       pl.lon AS loc_lon, pl.lat AS loc_lat, pl.recorded_at AS loc_at
FROM s, ride_offers o
JOIN users u ON u.id = o.provider_id
JOIN rider_profiles rp ON rp.user_id = o.provider_id
LEFT JOIN LATERAL (SELECT ST_X(geom) AS lon, ST_Y(geom) AS lat, recorded_at FROM provider_locations
                   WHERE user_id = o.provider_id ORDER BY recorded_at DESC LIMIT 1) pl ON true
WHERE o.state = 'published' AND o.seats_available > 0
  AND o.provider_id <> %(me)s
  AND rp.service_on AND rp.rider_status = 'verified'          -- Service OFF => not visible (AT-05)
  AND u.identity_status = 'verified'
  AND (u.suspended_until IS NULL OR u.suspended_until < now())
  AND o.departure_at BETWEEN %(a)s AND %(b)s
  AND o.route_geom && ST_Expand(s.g, 0.001)                   -- GiST bounding-box prefilter
ORDER BY o.departure_at
LIMIT %(lim)s
"""

@bp.post("/search")
@require_auth
@require_category("student")                 # professionals are blocked by the backend (AT-02)
@require_contact_verified
@require_verified_identity
def search():
    d = SearchIn.model_validate(request.get_json(silent=True) or {})
    geo = json.dumps(d.route.model_dump())
    chk = fetch_one("""SELECT ST_IsValid(g) AS valid, ST_Length(g::geography) AS m
                       FROM (SELECT ST_SetSRID(ST_GeomFromGeoJSON(%s),4326) AS g) t""", (geo,))
    if not chk["valid"] or chk["m"] <= 0:
        raise HttpError(400, "Invalid route geometry (FR-024)")
    pickup = tuple(d.route.coordinates[0])
    now = datetime.now(timezone.utc)
    visible = []
    with tx() as cur:
        cur.execute(CANDIDATE_SQL, {"route": geo, "tol": matching.CORRIDOR_TOLERANCE_M, "me": str(g.user["id"]),
                                    "a": d.depart_after, "b": d.depart_before, "lim": MAX_CANDIDATES})
        for c in cur.fetchall():
            # FR-018: latest usable provider location, else the planned start of the offer
            fresh = c["loc_lat"] is not None and c["loc_at"] is not None and now - c["loc_at"] <= LOCATION_MAX_AGE
            origin = (c["loc_lon"], c["loc_lat"]) if fresh else (c["start_lon"], c["start_lat"])
            dec = matching.decide(bool(c["covered"]), float(c["overlap_m"] or 0), float(c["provider_m"] or 0),
                                  origin, pickup, routing.road_distance_m)
            cur.execute("""INSERT INTO match_decisions(offer_id,student_id,route_version,contained,match_bps,
                                                       road_distance_m,visible,reason)
                           VALUES(%s,%s,%s,%s,%s,%s,%s,%s)""",
                        (c["id"], g.user["id"], c["route_version"], dec.contained, dec.match_bps,
                         dec.road_distance_m, dec.visible, dec.reason))
            if dec.visible:
                visible.append({
                    "offerId": str(c["id"]), "provider": c["provider_first_name"],   # first name only (privacy)
                    "origin": c["origin_name"], "destination": c["destination_name"],
                    "departureAt": c["departure_at"].isoformat(), "windowMinutes": c["window_minutes"],
                    "fareBdt": str(c["fare_bdt"]), "routeKm": str(c["route_length_km"]),
                    "matchPercent": dec.match_bps / 100, "roadDistanceKm": round(dec.road_distance_m / 1000, 2)})
    visible.sort(key=lambda x: (-x["matchPercent"], x["departureAt"]))
    return jsonify(count=len(visible[:d.limit]), offers=visible[:d.limit])

@bp.post("/provider-location")
@provider_guard
def provider_location():
    """Provider shares current location. Only while Service is ON (FR-015, SEC-005)."""
    loc = LocationIn.model_validate(request.get_json(silent=True) or {})
    with tx() as cur:
        cur.execute("SELECT service_on FROM rider_profiles WHERE user_id=%s", (g.user["id"],))
        r = cur.fetchone()
        if not r or not r["service_on"]:
            raise HttpError(409, "Turn Service ON before sharing location", "SERVICE_OFF")
        cur.execute("INSERT INTO provider_locations(user_id,geom) VALUES(%s, ST_SetSRID(ST_MakePoint(%s,%s),4326))",
                    (g.user["id"], loc.lon, loc.lat))
    return jsonify(ok=True)
