"""No database needed.  Run: python -m unittest discover -s tests -v"""
import importlib.util, pathlib
_spec = importlib.util.spec_from_file_location("booking_rules", pathlib.Path(__file__).parent.parent / "app/services/booking_rules.py")
br = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(br)

import unittest

class CancelRuleTests(unittest.TestCase):
    def test_pending_and_confirmed_can_cancel(self):
        self.assertEqual(br.cancel_allowed("pending", False), (True, None))
        self.assertEqual(br.cancel_allowed("confirmed", False), (True, None))

    def test_already_cancelled_or_completed_cannot(self):
        self.assertEqual(br.cancel_allowed("cancelled", False), (False, "NOT_CANCELLABLE"))
        self.assertEqual(br.cancel_allowed("completed", False), (False, "NOT_CANCELLABLE"))

    def test_cannot_cancel_after_trip_started(self):
        self.assertEqual(br.cancel_allowed("confirmed", True), (False, "TRIP_STARTED"))

    def test_hold_is_ten_minutes_proposed(self):
        self.assertEqual(br.HOLD_MINUTES, 10)

if __name__ == "__main__":
    unittest.main()
