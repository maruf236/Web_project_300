-- Week 4 (Ali): provider live location + match decision log. Safe to run on an existing database.
CREATE TABLE IF NOT EXISTS provider_locations (
  id bigserial PRIMARY KEY,
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  geom geometry(Point,4326) NOT NULL,
  recorded_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS provider_locations_latest_ix ON provider_locations (user_id, recorded_at DESC);

-- UC-009 postcondition "Decision logged" (internal only, never shown to students)
CREATE TABLE IF NOT EXISTS match_decisions (
  id bigserial PRIMARY KEY,
  offer_id uuid NOT NULL REFERENCES ride_offers(id) ON DELETE CASCADE,
  student_id uuid NOT NULL REFERENCES users(id),
  route_version int NOT NULL,
  contained boolean NOT NULL,
  match_bps int,                 -- provider-side match in basis points (8000 = 80.00%)
  road_distance_m int,
  visible boolean NOT NULL,
  reason text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS match_decisions_offer_ix ON match_decisions (offer_id, created_at DESC);
