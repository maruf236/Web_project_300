"""Run:  python -m unittest discover -s tests -v     (no database needed). AT-06, AT-07, AT-08, FR-019."""
import unittest
import importlib.util, pathlib
_spec = importlib.util.spec_from_file_location("matching", pathlib.Path(__file__).parent.parent / "app/services/matching.py")
_m = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(_m)   # loads rules without Flask
decide, provider_match_bps, RoutingError, MATCH_MIN_BPS = _m.decide, _m.provider_match_bps, _m.RoutingError, _m.MATCH_MIN_BPS

O, P = (90.37, 23.74), (90.38, 23.75)
def road(m): return lambda a, b: m
def boom(a, b): raise RoutingError("down")

class MatchingTests(unittest.TestCase):
    def test_at08_boundary_79_99_fails_80_00_passes(self):
        self.assertEqual(provider_match_bps(7999, 10000), 7999)
        self.assertEqual(provider_match_bps(8000, 10000), 8000)
        self.assertFalse(decide(True, 7999, 10000, O, P, road(5000)).visible)
        self.assertTrue(decide(True, 8000, 10000, O, P, road(5000)).visible)

    def test_no_rounding_up(self):
        self.assertLess(provider_match_bps(79.999, 100), MATCH_MIN_BPS)   # 79.999% must not become 80%

    def test_at06_road_distance_0_99_hidden_1_00_visible(self):
        self.assertEqual(decide(True, 10000, 10000, O, P, road(999)).reason, "closer_than_1km")
        self.assertTrue(decide(True, 10000, 10000, O, P, road(1000)).visible)

    def test_at07_route_not_contained_rejected(self):
        d = decide(False, 6000, 10000, O, P, road(5000))
        self.assertFalse(d.visible); self.assertEqual(d.reason, "not_contained")

    def test_fr019_routing_failure_hides_offer(self):
        d = decide(True, 10000, 10000, O, P, boom)
        self.assertFalse(d.visible); self.assertEqual(d.reason, "routing_failed")

    def test_fr024_invalid_geometry(self):
        self.assertEqual(decide(True, 0, 0, O, P, road(5000)).reason, "invalid_geometry")

    def test_both_conditions_required(self):
        self.assertFalse(decide(False, 10000, 10000, O, P, road(5000)).visible)   # 80% ok, not contained
        self.assertFalse(decide(True, 5000, 10000, O, P, road(5000)).visible)     # contained, 50%

    def test_overlap_larger_than_provider_is_capped(self):
        self.assertEqual(provider_match_bps(12000, 10000), 10000)

if __name__ == "__main__":
    unittest.main()
