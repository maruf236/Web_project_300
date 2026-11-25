-- Week 5 (Ali): booking columns. Safe to re-run (IF NOT EXISTS). Run AFTER schema.sql and 004.
ALTER TABLE bookings
  ADD COLUMN IF NOT EXISTS route_version   int NOT NULL DEFAULT 1,   -- offer route version at booking time (FR-025)
  ADD COLUMN IF NOT EXISTS hold_expires_at timestamptz,              -- seat hold deadline while 'pending' (OR-04)
  ADD COLUMN IF NOT EXISTS idempotency_key text,                     -- safe retry of the same booking request
  ADD COLUMN IF NOT EXISTS match_bps       int,
  ADD COLUMN IF NOT EXISTS road_distance_m int,
  ADD COLUMN IF NOT EXISTS student_route   geometry(LineString,4326),
  ADD COLUMN IF NOT EXISTS cancelled_by    uuid REFERENCES users(id),  -- NULL = system (hold expired)
  ADD COLUMN IF NOT EXISTS cancelled_at    timestamptz,
  ADD COLUMN IF NOT EXISTS cancel_reason   text;                      -- FR-044: actor, time, reason

CREATE UNIQUE INDEX IF NOT EXISTS bookings_idem_uq ON bookings (student_id, idempotency_key) WHERE idempotency_key IS NOT NULL;
CREATE INDEX IF NOT EXISTS bookings_hold_ix    ON bookings (hold_expires_at) WHERE state = 'pending';
CREATE INDEX IF NOT EXISTS bookings_student_ix ON bookings (student_id, created_at DESC);
CREATE INDEX IF NOT EXISTS bookings_offer_ix   ON bookings (offer_id);
