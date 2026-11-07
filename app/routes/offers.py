import json
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional
from uuid import UUID
from flask import Blueprint, request, jsonify, g
from pydantic import BaseModel, Field, field_validator
from ..config import Config
from ..db import tx, fetch_one, fetch_all, execute, audit
from ..errors import HttpError
from ..security import require_auth, require_contact_verified, require_verified_identity

bp = Blueprint("offers", __name__)

def require_approved_provider(fn):
    """Backend gate for FR-007/FR-008 (AT-03): rider + vehicle must be approved and unexpired."""
    from functools import wraps
    @wraps(fn)
    def wrapper(*a, **kw):
        p = fetch_one("SELECT rider_status, licence_expiry FROM rider_profiles WHERE user_id=%s", (g.user["id"],))
        if not p or p["rider_status"] != "verified" or (p["licence_expiry"] and p["licence_expiry"] < datetime.now().date()):
            raise HttpError(403, "Rider and vehicle not approved", "PROVIDER_NOT_APPROVED")
        v = fetch_one("""SELECT 1 FROM vehicles WHERE owner_id=%s
                         AND (registration_expiry IS NULL OR registration_expiry>=current_date) LIMIT 1""", (g.user["id"],))
        if not v:
            raise HttpError(403, "No valid vehicle registration", "PROVIDER_NOT_APPROVED")
        return fn(*a, **kw)
    return wrapper

def provider_guard(fn):
    return require_auth(require_contact_verified(require_verified_identity(require_approved_provider(fn))))

class Route(BaseModel):
    type: str
    coordinates: List[List[float]] = Field(min_length=2, max_length=5000)

    @field_validator("type")
    @classmethod
    def _t(cls, v):
        if v != "LineString":
            raise ValueError("Route must be a GeoJSON LineString")
        return v

    @field_validator("coordinates")
    @classmethod
    def _c(cls, pts):
        for p in pts:   # [lon, lat] inside Bangladesh bounding box
            if len(p) != 2 or not (88 <= p[0] <= 93 and 20.5 <= p[1] <= 26.7):
                raise ValueError("Coordinates must be [lon, lat] inside Bangladesh")
        return pts

class OfferIn(BaseModel):
    origin_name: str = Field(min_length=2, max_length=200)
    destination_name: str = Field(min_length=2, max_length=200)
    route: Route
    departure_at: datetime
    window_minutes: int = Field(default=0, ge=0, le=180)
    fare_bdt: Decimal = Field(ge=0)
    vehicle_id: Optional[UUID] = None

def _money(x): return Decimal(x).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

@bp.post("")
@provider_guard
def publish_offer():
    """UC-006 / FR-012 / FR-016: publish an existing planned journey with a fixed route."""
    d = OfferIn.model_validate(request.get_json(silent=True) or {})
    dep = d.departure_at if d.departure_at.tzinfo else d.departure_at.replace(tzinfo=timezone.utc)
    if dep <= datetime.now(timezone.utc):
        raise HttpError(400, "Departure must be in the future")
    geo = json.dumps(d.route.model_dump())
    with tx() as cur:
        cur.execute("""SELECT ST_IsValid(g) AS valid, ST_Length(g::geography)/1000.0 AS km
                       FROM (SELECT ST_SetSRID(ST_GeomFromGeoJSON(%s),4326) AS g) t""", (geo,))
        r = cur.fetchone()
        km = Decimal(r["km"]).quantize(Decimal("0.001"))
        if not r["valid"] or km <= 0:
            raise HttpError(400, "Invalid route geometry (FR-024)")
        base = _money(km * Config.BASE_RATE_BDT_PER_KM)           # FR-030
        fare = _money(d.fare_bdt)
        if fare > base:                                            # FR-031: base, less, or zero
            raise HttpError(400, f"Fare cannot exceed base fare BDT {base}")
        cur.execute("""INSERT INTO ride_offers(provider_id,vehicle_id,origin_name,destination_name,route_geom,
                         route_length_km,departure_at,window_minutes,seats_total,seats_available,base_fare_bdt,fare_bdt)
                       VALUES(%s,%s,%s,%s,ST_SetSRID(ST_GeomFromGeoJSON(%s),4326),%s,%s,%s,1,1,%s,%s)
                       RETURNING id,route_length_km,base_fare_bdt,fare_bdt,state,route_version""",
                    (g.user["id"], str(d.vehicle_id) if d.vehicle_id else None, d.origin_name, d.destination_name,
                     geo, km, dep, d.window_minutes, base, fare))
        offer = cur.fetchone()
        cur.execute("INSERT INTO ride_route_versions(offer_id,version,route_geom) SELECT id,1,route_geom FROM ride_offers WHERE id=%s",
                    (offer["id"],))
        audit(cur, g.user["id"], "offer.publish", "ride_offer", offer["id"])
    return jsonify({k: (str(v) if isinstance(v, (Decimal, UUID)) else v) for k, v in offer.items()}), 201

@bp.get("/mine")
@require_auth
def my_offers():
    rows = fetch_all("""SELECT id,origin_name,destination_name,departure_at,seats_available,fare_bdt,base_fare_bdt,
                               route_length_km,state,route_version
                        FROM ride_offers WHERE provider_id=%s ORDER BY departure_at DESC LIMIT 100""", (g.user["id"],))
    return jsonify([{k: (str(v) if isinstance(v, (Decimal, UUID)) else (v.isoformat() if isinstance(v, datetime) else v))
                     for k, v in r.items()} for r in rows])

@bp.patch("/service")
@provider_guard
def set_service():
    """UC-007 / FR-011,014,015: Service ON/OFF (OFF removes availability from search)."""
    on = (request.get_json(silent=True) or {}).get("on")
    if not isinstance(on, bool):
        raise HttpError(400, "'on' must be true or false")
    with tx() as cur:
        cur.execute("""INSERT INTO rider_profiles(user_id,service_on) VALUES(%s,%s)
                       ON CONFLICT (user_id) DO UPDATE SET service_on=EXCLUDED.service_on""", (g.user["id"], on))
        audit(cur, g.user["id"], "service.on" if on else "service.off", "user", g.user["id"])
    return jsonify(serviceOn=on)

@bp.patch("/<uuid:offer_id>/cancel")
@require_auth
def cancel_offer(offer_id):
    """Owner only. Routes are never edited after publish (FR-025)."""
    with tx() as cur:
        cur.execute("""UPDATE ride_offers SET state='cancelled', seats_available=0
                       WHERE id=%s AND provider_id=%s AND state='published'""", (str(offer_id), g.user["id"]))
        if cur.rowcount == 0:
            raise HttpError(404, "Offer not found or not cancellable")
        audit(cur, g.user["id"], "offer.cancel", "ride_offer", offer_id)
    return jsonify(ok=True)
