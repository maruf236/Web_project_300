-- RIDEVAI schema (PostgreSQL 15 + PostGIS). Week 2, owner: Ali.
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TYPE user_category AS ENUM ('student','professional');
CREATE TYPE staff_role AS ENUM ('none','verification_officer','complaint_officer','payment_reviewer','admin');
CREATE TYPE verif_status AS ENUM ('pending','verified','rejected','reverification_required','suspended');
CREATE TYPE ride_state AS ENUM ('draft','published','full','expired','cancelled');
CREATE TYPE booking_state AS ENUM ('pending','confirmed','cancelled','completed');
CREATE TYPE payment_state AS ENUM ('initiated','confirmed','failed','refunded');
CREATE TYPE trip_state AS ENUM ('in_progress','completed','review_required','cancelled');

CREATE TABLE users (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  category user_category NOT NULL,
  staff_role staff_role NOT NULL DEFAULT 'none',
  full_name text NOT NULL,
  email text NOT NULL,
  phone text NOT NULL,
  password_hash text NOT NULL,
  email_verified_at timestamptz,
  phone_verified_at timestamptz,
  identity_status verif_status NOT NULL DEFAULT 'pending',
  suspended_until timestamptz,
  consent_at timestamptz NOT NULL DEFAULT now(),
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX users_email_uq ON users (lower(email));
CREATE UNIQUE INDEX users_phone_uq ON users (phone);

CREATE TABLE email_tokens (
  token_hash text PRIMARY KEY,
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  expires_at timestamptz NOT NULL,
  used_at timestamptz
);

CREATE TABLE otp_codes (
  id bigserial PRIMARY KEY,
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  code_hash text NOT NULL,
  expires_at timestamptz NOT NULL,
  attempts int NOT NULL DEFAULT 0,
  used_at timestamptz
);

CREATE TABLE student_profiles (
  user_id uuid PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  institution text, student_id_no text, institution_email text,
  institution_email_verified_at timestamptz,
  enrolment_valid_until date
);
CREATE TABLE professional_profiles (
  user_id uuid PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  employer text, official_email text, official_email_verified_at timestamptz,
  status_valid_until date
);

CREATE TABLE verification_documents (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  doc_type text NOT NULL,           -- nid, student_id, enrolment, licence, bike_reg ...
  storage_key text NOT NULL,        -- private encrypted bucket key, never public
  status verif_status NOT NULL DEFAULT 'pending',
  reviewer_id uuid REFERENCES users(id),
  reviewed_at timestamptz, reject_reason text,
  expires_on date,
  uploaded_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE rider_profiles (
  user_id uuid PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  rider_status verif_status NOT NULL DEFAULT 'pending',
  licence_expiry date, service_on boolean NOT NULL DEFAULT false
);
CREATE TABLE vehicles (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  reg_no text NOT NULL UNIQUE, model text, registration_expiry date
);

CREATE TABLE ride_offers (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  provider_id uuid NOT NULL REFERENCES users(id),
  vehicle_id uuid REFERENCES vehicles(id),
  origin_name text NOT NULL, destination_name text NOT NULL,
  route_geom geometry(LineString,4326) NOT NULL,
  route_version int NOT NULL DEFAULT 1,
  route_length_km numeric(8,3) NOT NULL CHECK (route_length_km > 0),
  departure_at timestamptz NOT NULL,
  window_minutes int NOT NULL DEFAULT 0 CHECK (window_minutes BETWEEN 0 AND 180),
  seats_total int NOT NULL CHECK (seats_total BETWEEN 1 AND 1),   -- motorcycle: 1 pillion seat
  seats_available int NOT NULL CHECK (seats_available >= 0),
  base_fare_bdt numeric(10,2) NOT NULL,
  fare_bdt numeric(10,2) NOT NULL CHECK (fare_bdt >= 0 AND fare_bdt <= base_fare_bdt),
  state ride_state NOT NULL DEFAULT 'published',
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ride_offers_geom_gix ON ride_offers USING GIST (route_geom);
CREATE INDEX ride_offers_avail_ix ON ride_offers (departure_at) WHERE state='published' AND seats_available>0;

CREATE TABLE ride_route_versions (
  offer_id uuid REFERENCES ride_offers(id) ON DELETE CASCADE,
  version int, route_geom geometry(LineString,4326) NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (offer_id, version)
);

CREATE TABLE bookings (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  offer_id uuid NOT NULL REFERENCES ride_offers(id),
  student_id uuid NOT NULL REFERENCES users(id),
  state booking_state NOT NULL DEFAULT 'pending',
  fare_bdt numeric(10,2) NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);
-- one live booking per offer seat: atomic guard (FR-028, AT-12)
CREATE UNIQUE INDEX bookings_one_live_per_offer ON bookings(offer_id) WHERE state IN ('pending','confirmed');

CREATE TABLE payment_attempts (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  booking_id uuid NOT NULL REFERENCES bookings(id),
  attempt_key text NOT NULL UNIQUE,
  gateway_payment_id text UNIQUE,
  amount_bdt numeric(10,2) NOT NULL, currency text NOT NULL DEFAULT 'BDT',
  state payment_state NOT NULL DEFAULT 'initiated',
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE trips (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  booking_id uuid NOT NULL UNIQUE REFERENCES bookings(id),
  state trip_state NOT NULL DEFAULT 'in_progress',
  started_at timestamptz, ended_at timestamptz,
  start_point geometry(Point,4326), end_point geometry(Point,4326),
  actual_distance_km numeric(8,3)
);
CREATE TABLE gps_points (
  id bigserial PRIMARY KEY, trip_id uuid REFERENCES trips(id) ON DELETE CASCADE,
  geom geometry(Point,4326) NOT NULL, recorded_at timestamptz NOT NULL,
  UNIQUE (trip_id, recorded_at)          -- duplicate events ignored (FR-039)
);

CREATE TABLE complaints (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(), reporter_id uuid REFERENCES users(id),
  booking_id uuid REFERENCES bookings(id), kind text NOT NULL, details text,
  status text NOT NULL DEFAULT 'open', created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE no_shows (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(), booking_id uuid REFERENCES bookings(id),
  accused_id uuid REFERENCES users(id), status text NOT NULL DEFAULT 'reported',
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE notifications (
  id bigserial PRIMARY KEY, user_id uuid REFERENCES users(id), channel text NOT NULL,
  event text NOT NULL, body text, sent_at timestamptz, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE audit_log (
  id bigserial PRIMARY KEY, actor_id uuid, action text NOT NULL, record_type text,
  record_id text, reason text, created_at timestamptz NOT NULL DEFAULT now()
);
