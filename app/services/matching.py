"""Pure matching rules (no database, no Flask) so they are easy to unit-test. Owner: Ali.

Rules (SRS FR-017..FR-024), checked cheapest-first:
  1. provider geometry valid                      (FR-024)
  2. student route 100% inside provider route     (FR-020)  -> `covered` computed by PostGIS
  3. provider-side match >= 80%                   (FR-021)  -> integer basis points, floored
  4. ROAD distance provider -> student >= 1 km    (FR-017)  -> routing service, never straight-line (FR-019)
Both 2 and 3 must pass together (FR-022).
"""
from dataclasses import dataclass
from decimal import Decimal, ROUND_FLOOR
from typing import Callable, Optional, Tuple

MATCH_MIN_BPS = 8000        # 80.00%  (FR-021)
MIN_ROAD_DISTANCE_M = 1000  # 1 km    (FR-017)
CORRIDOR_TOLERANCE_M = 15   # GPS/road-snapping tolerance. PROPOSED, needs approval (OR-01)

class RoutingError(Exception):
    """Road routing failed or returned nothing usable. The offer must be hidden (FR-019)."""

@dataclass
class Decision:
    visible: bool
    reason: str
    contained: bool
    match_bps: Optional[int] = None
    road_distance_m: Optional[int] = None

def provider_match_bps(overlap_m: float, provider_len_m: float) -> int:
    """OR-01 (OPEN): proposed formula = shared length / provider route length.
    Floored to whole basis points so 79.99% can never round up to 80.00% (AT-08).
    Change ONLY this function when the supervisor approves a different denominator."""
    if provider_len_m <= 0:
        return 0
    bps = (Decimal(str(overlap_m)) * 10000 / Decimal(str(provider_len_m))).to_integral_value(rounding=ROUND_FLOOR)
    return int(max(0, min(10000, bps)))

def decide(covered: bool, overlap_m: float, provider_len_m: float,
           origin: Tuple[float, float], pickup: Tuple[float, float],
           road_distance_fn: Callable[[Tuple[float, float], Tuple[float, float]], float]) -> Decision:
    """origin / pickup are (lon, lat). road_distance_fn returns metres or raises RoutingError."""
    if provider_len_m is None or provider_len_m <= 0:
        return Decision(False, "invalid_geometry", False)
    if not covered:
        return Decision(False, "not_contained", False)
    bps = provider_match_bps(overlap_m, provider_len_m)
    if bps < MATCH_MIN_BPS:
        return Decision(False, "below_80_percent", True, bps)
    try:
        road_m = road_distance_fn(origin, pickup)
    except RoutingError:
        return Decision(False, "routing_failed", True, bps)          # never fall back to straight line
    road_m = int(road_m)
    if road_m < MIN_ROAD_DISTANCE_M:
        return Decision(False, "closer_than_1km", True, bps, road_m)
    return Decision(True, "match", True, bps, road_m)
