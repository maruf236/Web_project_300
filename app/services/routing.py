"""Road-distance client (OSRM HTTP API). Owner: Ali.
OSRM_URL defaults to the public demo server: fine for development ONLY.
For production self-host OSRM with the Bangladesh extract (Geofabrik) and set OSRM_URL."""
import json, os, urllib.request, urllib.error
from .matching import RoutingError

def road_distance_m(origin, dest, timeout=4):
    """origin/dest = (lon, lat). Returns road distance in metres, or raises RoutingError."""
    base = os.getenv("OSRM_URL", "https://router.project-osrm.org").rstrip("/")
    url = (f"{base}/route/v1/driving/{origin[0]:.6f},{origin[1]:.6f};{dest[0]:.6f},{dest[1]:.6f}"
           "?overview=false&alternatives=false")
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            data = json.load(r)
    except (urllib.error.URLError, TimeoutError, ValueError, OSError) as e:
        raise RoutingError(f"routing service unavailable: {e}")
    if data.get("code") != "Ok" or not data.get("routes"):
        raise RoutingError("no road route found")
    d = data["routes"][0].get("distance")
    if d is None or d < 0:
        raise RoutingError("invalid distance from routing service")
    return float(d)
