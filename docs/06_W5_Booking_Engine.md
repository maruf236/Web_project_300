# Week 5 — Booking & Atomic Seats (Owner: Ali Ahsan Maruf, "Maruf Week 5")
Covers FR-026..FR-029, FR-044..FR-046 (booking side), UC-010, UC-015, AT-01, AT-02, AT-12, AT-15, AT-16.

## New files only (nothing from Weeks 1-4 is edited)
- `app/services/booking_rules.py` — reserve seat, release expired holds, confirm, cancel (no Flask, testable alone)
- `app/routes/bookings.py` — the API
- `db/migrations/005_maruf_week5.sql` — extra columns/indexes on `bookings` (safe to re-run)
- `tests/test_booking_rules.py` (4 pure tests), `tests/test_booking_db.py` (5 DB tests incl. AT-12)
- `requests_week5.http`

## API
| Method | Path | Who |
|---|---|---|
| POST | /api/bookings/preview | verified student — shows provider, route, time, seat, FINAL fare; reserves nothing (FR-027) |
| POST | /api/bookings | verified student — re-checks the Week 4 match, then atomically takes the seat. Optional header `Idempotency-Key` |
| GET | /api/bookings/mine | student or provider — only their own bookings (FR-041) |
| GET | /api/bookings/<id> | a party to the booking, else 403 (AT-15) |
| PATCH | /api/bookings/<id>/cancel | student or provider; reason required (FR-044) |

## How the seat is protected (AT-12)
One guarded `UPDATE ride_offers SET seats_available = seats_available - 1 ... WHERE seats_available > 0`. PostgreSQL row-locks the offer, so simultaneous requests queue; the second finds 0 seats and gets `409 SEAT_TAKEN`. A unique partial index (one live booking per offer) is a second guard. Lock order is always offer first, then booking.

## Statuses (FR-029)
Booking: `pending` -> `confirmed` | `cancelled`. Payment and trip statuses stay in their own tables.

## For Sarwar (bKash, Week 5) and later weeks
- After **trusted gateway confirmation only** call `booking_rules.confirm_booking(cur, booking_id)`. If it returns `None` the hold had already been released: refund/reconcile (OR-03).
- Expired holds are released lazily before each new booking. Optional: call `release_expired_holds(cur)` from a scheduled job.
- Trips (Week 6) should insert into `trips(booking_id)`; cancel is then blocked automatically (`TRIP_STARTED`).

## Assumptions to approve
- Seat hold = 10 minutes (OR-04 is OPEN; one constant `HOLD_MINUTES`).
- Provider cancelling a booking withdraws the whole offer; no replacement is assigned (FR-045). Student cancel re-opens the seat.
- A student cannot book their own offer; one live booking per student per offer.
- Cancellation never touches no-show counts (FR-046, AT-16): this module never writes to `no_shows`.

## Known gaps (honest)
- Database code was not run here (no PostgreSQL in my environment). Run `python -m unittest tests.test_booking_db -v` once; it also proves AT-12 with 20 parallel requests.
- Cancelling an **offer** (`PATCH /api/offers/<id>/cancel`, Week 3) does not yet cancel its live bookings. Easy follow-up; tell me if you want it.
- Refunds, payment timing and the final fare engine belong to Sarwar (bKash) and Week 6 (fare).
