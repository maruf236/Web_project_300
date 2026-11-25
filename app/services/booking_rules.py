"""Seat reservation engine. Owner: Ali (Week 5). Needs only a psycopg2 cursor (no Flask), so it is testable alone.

Atomicity (FR-028, AT-12): the seat is taken by ONE guarded UPDATE
    UPDATE ride_offers SET seats_available = seats_available - 1 ... WHERE seats_available > 0
PostgreSQL row-locks the offer, so two simultaneous requests are serialised: the second one re-checks the
WHERE condition after the first commits, finds 0 seats and updates 0 rows -> SeatUnavailable.
A UNIQUE partial index on bookings(offer_id) for live bookings is a second, independent guard.

Lock order everywhere: ride_offers row FIRST, then bookings row (prevents deadlocks).
Booking, payment and trip statuses stay separate (FR-029): this module only touches booking state.
"""
HOLD_MINUTES = 10   # PROPOSED (OR-04 is OPEN): unpaid pending booking releases its seat after this long

class SeatUnavailable(Exception):
    pass

class AlreadyBooked(Exception):
    pass

class IdempotencyMismatch(Exception):
    pass

class BookingError(Exception):
    """code: NOT_FOUND | FORBIDDEN | NOT_CANCELLABLE | TRIP_STARTED"""
    def __init__(self, code, message):
        super().__init__(message)
        self.code, self.message = code, message

def cancel_allowed(state, trip_started):
    """Pure rule (UC-015): only pending/confirmed bookings, and never after the trip has started."""
    if trip_started:
        return False, "TRIP_STARTED"
    if state not in ("pending", "confirmed"):
        return False, "NOT_CANCELLABLE"
    return True, None

def reserve_seat(cur, offer_id, student_id, route_geojson, match_bps, road_distance_m, idem_key=None):
    """Returns (booking_row, created). created=False means an identical earlier request was replayed."""
    if idem_key:
        cur.execute("SELECT * FROM bookings WHERE student_id=%s AND idempotency_key=%s", (str(student_id), idem_key))
        old = cur.fetchone()
        if old:
            if str(old["offer_id"]) != str(offer_id):
                raise IdempotencyMismatch()
            return old, False
    cur.execute("""SELECT 1 FROM bookings WHERE student_id=%s AND offer_id=%s AND state IN ('pending','confirmed')""",
                (str(student_id), str(offer_id)))
    if cur.fetchone():
        raise AlreadyBooked()
    cur.execute("""UPDATE ride_offers
                      SET seats_available = seats_available - 1,
                          state = CASE WHEN seats_available - 1 = 0 THEN 'full'::ride_state ELSE state END
                    WHERE id=%s AND state='published' AND seats_available > 0
                      AND departure_at > now() AND provider_id <> %s
                RETURNING fare_bdt, route_version""", (str(offer_id), str(student_id)))
    got = cur.fetchone()
    if not got:
        raise SeatUnavailable()
    cur.execute("""INSERT INTO bookings(offer_id,student_id,state,fare_bdt,route_version,hold_expires_at,
                                        idempotency_key,match_bps,road_distance_m,student_route)
                   VALUES(%s,%s,'pending',%s,%s, now() + make_interval(mins => %s), %s,%s,%s,
                          ST_SetSRID(ST_GeomFromGeoJSON(%s),4326))
                   RETURNING id, offer_id, state, fare_bdt, hold_expires_at, created_at""",
                (str(offer_id), str(student_id), got["fare_bdt"], got["route_version"], HOLD_MINUTES,
                 idem_key, match_bps, road_distance_m, route_geojson))
    return cur.fetchone(), True

def release_expired_holds(cur):
    """Cancel unpaid pending bookings whose hold ran out and give the seat back. Returns number released.
    Called lazily before each booking, and can also be scheduled by Sarwar's deployment job."""
    cur.execute("""SELECT DISTINCT offer_id FROM bookings
                    WHERE state='pending' AND hold_expires_at IS NOT NULL AND hold_expires_at < now()""")
    ids = [str(r["offer_id"]) for r in cur.fetchall()]
    if not ids:
        return 0
    # lock offers first (same order as everywhere), skip ones another request is working on
    cur.execute("SELECT id FROM ride_offers WHERE id = ANY(%s::uuid[]) ORDER BY id FOR UPDATE SKIP LOCKED", (ids,))
    locked = [str(r["id"]) for r in cur.fetchall()]
    if not locked:
        return 0
    cur.execute("""UPDATE bookings SET state='cancelled', cancelled_at=now(), cancel_reason='hold_expired'
                    WHERE offer_id = ANY(%s::uuid[]) AND state='pending'
                      AND hold_expires_at IS NOT NULL AND hold_expires_at < now()
                RETURNING offer_id""", (locked,))
    freed = [str(r["offer_id"]) for r in cur.fetchall()]
    if freed:
        cur.execute("""UPDATE ride_offers
                          SET seats_available = LEAST(seats_total, seats_available + 1),
                              state = CASE WHEN state='full' AND departure_at > now() THEN 'published'::ride_state ELSE state END
                        WHERE id = ANY(%s::uuid[]) AND state IN ('published','full')""", (freed,))
    return len(freed)

def confirm_booking(cur, booking_id):
    """For the bKash module (Sarwar): call ONLY after trusted gateway confirmation (FR-033).
    Returns the booking row, or None if it is no longer pending (e.g. the hold was already released) --
    in that case the caller must refund/reconcile (OR-03). Payment status is stored elsewhere (FR-029)."""
    cur.execute("""UPDATE bookings SET state='confirmed', hold_expires_at=NULL
                    WHERE id=%s AND state='pending' RETURNING id, offer_id, student_id, state, fare_bdt""", (str(booking_id),))
    return cur.fetchone()

def cancel_booking(cur, booking_id, actor_id, reason):
    """UC-015 / FR-044..046. Records actor, time, reason; notifies the other party.
    Never touches no-show counts (FR-046) and never assigns a replacement (FR-045)."""
    cur.execute("SELECT offer_id FROM bookings WHERE id=%s", (str(booking_id),))
    row = cur.fetchone()
    if not row:
        raise BookingError("NOT_FOUND", "Booking not found")
    cur.execute("SELECT id, provider_id FROM ride_offers WHERE id=%s FOR UPDATE", (str(row["offer_id"]),))
    offer = cur.fetchone()
    cur.execute("SELECT * FROM bookings WHERE id=%s FOR UPDATE", (str(booking_id),))
    b = cur.fetchone()
    actor = str(actor_id)
    if actor == str(b["student_id"]):
        role, other = "student", str(offer["provider_id"])
    elif actor == str(offer["provider_id"]):
        role, other = "provider", str(b["student_id"])
    else:
        raise BookingError("FORBIDDEN", "Not your booking")
    cur.execute("SELECT 1 FROM trips WHERE booking_id=%s", (str(booking_id),))
    ok, code = cancel_allowed(b["state"], cur.fetchone() is not None)
    if not ok:
        raise BookingError(code, "This booking can no longer be cancelled")
    cur.execute("""UPDATE bookings SET state='cancelled', cancelled_by=%s, cancelled_at=now(), cancel_reason=%s
                    WHERE id=%s""", (actor, reason, str(booking_id)))
    if role == "student":
        cur.execute("""UPDATE ride_offers
                          SET seats_available = LEAST(seats_total, seats_available + 1),
                              state = CASE WHEN state='full' AND departure_at > now() THEN 'published'::ride_state ELSE state END
                        WHERE id=%s AND state IN ('published','full')""", (str(offer["id"]),))
    else:  # provider cancelled: the offer is withdrawn, no replacement is assigned (FR-045). ASSUMPTION, see docs.
        cur.execute("UPDATE ride_offers SET state='cancelled', seats_available=0 WHERE id=%s", (str(offer["id"]),))
    cur.execute("""INSERT INTO notifications(user_id,channel,event,body) VALUES(%s,'in_app','booking.cancelled',%s)""",
                (other, f"A booking was cancelled by the {role}. Reason: {reason}"))
    return {"id": str(booking_id), "state": "cancelled", "cancelledBy": role}
