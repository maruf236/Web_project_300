"""Booking & atomic seat reservation (UC-010, UC-015, UC-014 partly). Owner: Ali (Week 5).
Matching rules are re-checked at booking time with the Week 4 engine, so a stale search result cannot be booked."""
import json, re
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID
from flask import Blueprint, request, jsonify, g
from pydantic import BaseModel, Field
from ..db import tx, fetch_one, fetch_all, audit
from ..errors import HttpError
from ..security import (require_auth, require_contact_verified, require_verified_identity, require_category)
from ..services import matching, routing, booking_rules as br
from .offers import Route

bp = Blueprint("bookings", __name__)
LOCATION_MAX_AGE = timedelta(minutes=15)   # same "usable location" rule as search (FR-018)

def student_guard(fn):   # only verified Students may create passenger bookings (FR-026, AT-02)
    return require_auth(require_category("student")(require_contact_verified(require_verified_identity(fn))))

class BookIn(BaseModel):
    offer_id: UUID
    route: Route

class CancelIn(BaseModel):
    reason: str = Field(min_length=3, max_length=500)

def _safe(v):
    if isinstance(v, (Decimal, UUID)): return str(v)
    if isinstance(v, datetime): return v.isoformat()
    if isinstance(v, dict): return {k: _safe(x) for k, x in v.items()}
    if isinstance(v, list): return [_safe(x) for x in v]
    return v

EVAL_SQL = """
WITH s AS (SELECT ST_SetSRID(ST_GeomFromGeoJSON(%(route)s),4326) AS g)
SELECT o.id, o.provider_id, o.origin_name, o.destination_name, o.departure_at, o.window_minutes, o.fare_bdt,
       o.route_length_km, o.route_version, o.state, o.seats_available, rp.service_on, rp.rider_status,
       u.identity_status, u.suspended_until, split_part(u.full_name,' ',1) AS provider_first_name,
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
WHERE o.id = %(oid)s
"""

def _evaluate(offer_id, route):
    """Returns (offer_row, decision). Raises HttpError if the offer is gone or not bookable."""
    geo = json.dumps(route.model_dump())
    chk = fetch_one("""SELECT ST_IsValid(g) AS valid, ST_Length(g::geography) AS m
                       FROM (SELECT ST_SetSRID(ST_GeomFromGeoJSON(%s),4326) AS g) t""", (geo,))
    if not chk["valid"] or chk["m"] <= 0:
        raise HttpError(400, "Invalid route geometry (FR-024)")
    pickup = tuple(route.coordinates[0])
    now = datetime.now(timezone.utc)
    with tx() as cur:
        cur.execute(EVAL_SQL, {"route": geo, "tol": matching.CORRIDOR_TOLERANCE_M, "oid": str(offer_id)})
        o = cur.fetchone()
        if not o:
            raise HttpError(404, "Offer not found")
        if str(o["provider_id"]) == str(g.user["id"]):
            raise HttpError(400, "You cannot book your own offer")
        suspended = o["suspended_until"] and o["suspended_until"] > now
        if not (o["state"] == "published" and o["seats_available"] > 0 and o["departure_at"] > now and o["service_on"]
                and o["rider_status"] == "verified" and o["identity_status"] == "verified" and not suspended):
            raise HttpError(409, "This offer is no longer available", "OFFER_UNAVAILABLE")
        fresh = o["loc_lat"] is not None and o["loc_at"] is not None and now - o["loc_at"] <= LOCATION_MAX_AGE
        origin = (o["loc_lon"], o["loc_lat"]) if fresh else (o["start_lon"], o["start_lat"])
        dec = matching.decide(bool(o["covered"]), float(o["overlap_m"] or 0), float(o["provider_m"] or 0),
                              origin, pickup, routing.road_distance_m)
        cur.execute("""INSERT INTO match_decisions(offer_id,student_id,route_version,contained,match_bps,
                                                   road_distance_m,visible,reason) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (o["id"], g.user["id"], o["route_version"], dec.contained, dec.match_bps,
                     dec.road_distance_m, dec.visible, dec.reason))
    if not dec.visible:
        raise HttpError(409, "This offer no longer matches your route", "NO_MATCH")
    return o, dec

def _summary(o, dec):   # FR-027: provider summary, route, time, seat and FINAL fare before confirmation
    return {"offerId": str(o["id"]), "provider": o["provider_first_name"], "origin": o["origin_name"],
            "destination": o["destination_name"], "departureAt": o["departure_at"].isoformat(),
            "windowMinutes": o["window_minutes"], "seats": 1, "finalFareBdt": str(o["fare_bdt"]),
            "currency": "BDT", "matchPercent": dec.match_bps / 100,
            "roadDistanceKm": round(dec.road_distance_m / 1000, 2), "paymentMethod": "bKash only",
            "seatHoldMinutes": br.HOLD_MINUTES}

@bp.post("/preview")
@student_guard
def preview():
    """Step before confirmation: shows the summary, reserves nothing."""
    d = BookIn.model_validate(request.get_json(silent=True) or {})
    o, dec = _evaluate(d.offer_id, d.route)
    return jsonify(_summary(o, dec))

@bp.post("")
@student_guard
def create_booking():
    """UC-010: re-check match, then atomically take the seat. Optional header Idempotency-Key makes retries safe."""
    d = BookIn.model_validate(request.get_json(silent=True) or {})
    key = request.headers.get("Idempotency-Key")
    if key is not None and not re.fullmatch(r"[A-Za-z0-9_\-]{8,100}", key):
        raise HttpError(400, "Idempotency-Key must be 8-100 letters, digits, _ or -")
    o, dec = _evaluate(d.offer_id, d.route)
    geo = json.dumps(d.route.model_dump())
    try:
        with tx() as cur:
            br.release_expired_holds(cur)
            b, created = br.reserve_seat(cur, d.offer_id, g.user["id"], geo, dec.match_bps, dec.road_distance_m, key)
            if created:
                audit(cur, g.user["id"], "booking.create", "booking", b["id"])
    except br.SeatUnavailable:
        raise HttpError(409, "The seat was just taken. Please search again.", "SEAT_TAKEN")
    except br.AlreadyBooked:
        raise HttpError(409, "You already have a booking on this offer", "ALREADY_BOOKED")
    except br.IdempotencyMismatch:
        raise HttpError(409, "Idempotency-Key was already used for a different offer", "IDEMPOTENCY_MISMATCH")
    body = {"booking": _safe(dict(b)), "summary": _summary(o, dec), "nextStep": "Pay with bKash before the hold expires"}
    return jsonify(body), (201 if created else 200)

_LIST_SQL = """
SELECT b.id, b.offer_id, b.state, b.fare_bdt, b.created_at, b.hold_expires_at, b.cancelled_at, b.cancel_reason,
       o.origin_name, o.destination_name, o.departure_at, o.provider_id, b.student_id,
       split_part(pu.full_name,' ',1) AS provider_first_name, split_part(su.full_name,' ',1) AS student_first_name
FROM bookings b JOIN ride_offers o ON o.id = b.offer_id
JOIN users pu ON pu.id = o.provider_id JOIN users su ON su.id = b.student_id
"""

def _row(r):
    me = str(g.user["id"])
    out = {k: r[k] for k in ("id", "offer_id", "state", "fare_bdt", "created_at", "hold_expires_at", "cancelled_at",
                             "cancel_reason", "origin_name", "destination_name", "departure_at")}
    out["myRole"] = "student" if str(r["student_id"]) == me else "provider"
    out["otherParty"] = r["provider_first_name"] if out["myRole"] == "student" else r["student_first_name"]
    return _safe(out)

@bp.get("/mine")
@require_auth
def my_bookings():
    """FR-041: only bookings where I am the student or the provider."""
    rows = fetch_all(_LIST_SQL + " WHERE b.student_id=%s OR o.provider_id=%s ORDER BY b.created_at DESC LIMIT 100",
                     (g.user["id"], g.user["id"]))
    return jsonify([_row(r) for r in rows])

@bp.get("/<uuid:booking_id>")
@require_auth
def get_booking(booking_id):
    r = fetch_one(_LIST_SQL + " WHERE b.id=%s", (str(booking_id),))
    if not r:
        raise HttpError(404, "Booking not found")
    if str(g.user["id"]) not in (str(r["student_id"]), str(r["provider_id"])):
        raise HttpError(403, "Access denied")          # AT-15
    return jsonify(_row(r))

@bp.patch("/<uuid:booking_id>/cancel")
@require_auth
def cancel(booking_id):
    d = CancelIn.model_validate(request.get_json(silent=True) or {})
    try:
        with tx() as cur:
            res = br.cancel_booking(cur, booking_id, g.user["id"], d.reason)
            audit(cur, g.user["id"], "booking.cancel", "booking", booking_id, d.reason)
    except br.BookingError as e:
        raise HttpError({"NOT_FOUND": 404, "FORBIDDEN": 403}.get(e.code, 409), e.message, e.code)
    return jsonify(res)
