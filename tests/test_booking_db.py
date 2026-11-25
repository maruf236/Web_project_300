"""Database tests for AT-12 (simultaneous seat requests) and hold/cancel seat release.
They SKIP automatically if PostgreSQL is not reachable. Needs: schema.sql + migrations 004 and 005 loaded,
and DATABASE_URL set (it is read from .env if python-dotenv is installed).
Run:  python -m unittest tests.test_booking_db -v
Uses its own temporary rows and deletes them afterwards."""
import importlib.util, os, pathlib, threading, unittest, uuid

try:
    from dotenv import load_dotenv; load_dotenv()
except Exception:
    pass
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except Exception:
    psycopg2 = None

_spec = importlib.util.spec_from_file_location("booking_rules", pathlib.Path(__file__).parent.parent / "app/services/booking_rules.py")
br = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(br)
ROUTE = '{"type":"LineString","coordinates":[[90.3742,23.7461],[90.3900,23.7800]]}'
DSN = os.getenv("DATABASE_URL")

def connect():
    c = psycopg2.connect(DSN); c.autocommit = False; return c

@unittest.skipUnless(psycopg2 and DSN, "psycopg2 / DATABASE_URL not available")
class BookingDbTests(unittest.TestCase):
    def setUp(self):
        try:
            self.c = connect()
        except Exception as e:
            self.skipTest(f"database not reachable: {e}")
        self.users = []
        self.provider = self._user("provider")
        cur = self.c.cursor(cursor_factory=RealDictCursor)
        cur.execute("""INSERT INTO ride_offers(provider_id,origin_name,destination_name,route_geom,route_length_km,
                         departure_at,seats_total,seats_available,base_fare_bdt,fare_bdt)
                       VALUES(%s,'A','B',ST_SetSRID(ST_GeomFromGeoJSON(%s),4326),4.0, now()+interval '1 day',1,1,40,40)
                       RETURNING id""", (self.provider, ROUTE))
        self.offer = cur.fetchone()["id"]; self.c.commit()

    def _user(self, tag):
        cur = self.c.cursor()
        u = uuid.uuid4(); n = u.int % 10**8
        cur.execute("""INSERT INTO users(id,category,full_name,email,phone,password_hash)
                       VALUES(%s,'student','Test User',%s,%s,'x')""", (str(u), f"{tag}-{u}@test.local", f"+88017{n:08d}"))
        self.c.commit(); self.users.append(str(u)); return str(u)

    def tearDown(self):
        if not hasattr(self, "c"):
            return
        self.c.rollback(); cur = self.c.cursor()
        cur.execute("DELETE FROM notifications WHERE user_id = ANY(%s::uuid[])", (self.users,))
        cur.execute("DELETE FROM bookings WHERE offer_id=%s", (str(self.offer),))
        cur.execute("DELETE FROM ride_offers WHERE id=%s", (str(self.offer),))
        cur.execute("DELETE FROM users WHERE id = ANY(%s::uuid[])", (self.users,))
        self.c.commit(); self.c.close()

    def _book(self, student, key=None):
        conn = connect()
        try:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            b, created = br.reserve_seat(cur, self.offer, student, ROUTE, 10000, 5000, key)
            conn.commit(); return b
        except Exception:
            conn.rollback(); raise
        finally:
            conn.close()

    def test_at12_simultaneous_requests_exactly_one_succeeds(self):
        students = [self._user("s") for _ in range(20)]
        results, barrier = [], threading.Barrier(len(students))
        def worker(s):
            barrier.wait()
            try: self._book(s); results.append("ok")
            except br.SeatUnavailable: results.append("taken")
        ts = [threading.Thread(target=worker, args=(s,)) for s in students]
        [t.start() for t in ts]; [t.join() for t in ts]
        self.assertEqual(results.count("ok"), 1)
        self.assertEqual(results.count("taken"), 19)
        cur = self.c.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT seats_available, state FROM ride_offers WHERE id=%s", (str(self.offer),))
        o = cur.fetchone(); self.assertEqual((o["seats_available"], o["state"]), (0, "full"))
        cur.execute("SELECT count(*) AS n FROM bookings WHERE offer_id=%s AND state IN ('pending','confirmed')", (str(self.offer),))
        self.assertEqual(cur.fetchone()["n"], 1)

    def test_same_student_cannot_book_twice(self):
        s = self._user("s"); self._book(s)
        with self.assertRaises((br.AlreadyBooked, br.SeatUnavailable)):
            self._book(s)

    def test_idempotent_retry_returns_same_booking(self):
        s = self._user("s"); b1 = self._book(s, "retry-key-0001"); b2 = self._book(s, "retry-key-0001")
        self.assertEqual(str(b1["id"]), str(b2["id"]))

    def test_expired_hold_releases_seat(self):
        s = self._user("s"); b = self._book(s)
        cur = self.c.cursor(cursor_factory=RealDictCursor)
        cur.execute("UPDATE bookings SET hold_expires_at = now() - interval '1 minute' WHERE id=%s", (str(b["id"]),))
        self.c.commit()
        self.assertEqual(br.release_expired_holds(cur), 1); self.c.commit()
        cur.execute("SELECT seats_available, state FROM ride_offers WHERE id=%s", (str(self.offer),))
        o = cur.fetchone(); self.assertEqual((o["seats_available"], o["state"]), (1, "published"))

    def test_student_cancel_releases_seat_provider_cancel_withdraws_offer(self):
        s = self._user("s"); b = self._book(s)
        cur = self.c.cursor(cursor_factory=RealDictCursor)
        br.cancel_booking(cur, b["id"], s, "changed my plan"); self.c.commit()
        cur.execute("SELECT seats_available, state FROM ride_offers WHERE id=%s", (str(self.offer),))
        o = cur.fetchone(); self.assertEqual((o["seats_available"], o["state"]), (1, "published"))
        s2 = self._user("s2"); b2 = self._book(s2)
        br.cancel_booking(cur, b2["id"], self.provider, "bike broke down"); self.c.commit()
        cur.execute("SELECT seats_available, state FROM ride_offers WHERE id=%s", (str(self.offer),))
        o = cur.fetchone(); self.assertEqual((o["seats_available"], o["state"]), (0, "cancelled"))
        with self.assertRaises(br.BookingError):
            br.cancel_booking(cur, b2["id"], s2, "again")      # already cancelled

if __name__ == "__main__":
    unittest.main()
