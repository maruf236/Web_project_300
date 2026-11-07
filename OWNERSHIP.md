# Who owns which files
All three parts live in ONE project (Flask needs them together). Each person edits mainly their own files and uses Git branches: `tamim-auth`, `ali-routing`, `sarwar-core`.

## MD. Jakaria Hafiz Tamim — Auth & Verification
- app/routes/auth.py (register, email verify, OTP, login, /me)
- app/security.py (JWT + RBAC decorators)
- docs/03_W2_Open_Decisions_Policy_Freeze.md
- Next: app/routes/verification.py, rider/vehicle approval, React auth pages

## Ali Ahsan Maruf — Routing & Booking
- db/schema.sql (tables, PostGIS, indexes)
- app/routes/offers.py (publish, my offers, Service ON/OFF, cancel)
- docs/01_W1_Spatial_Data_Plan.md
- Next: app/routes/search.py (1 km / 100% / 80% match), bookings, fare

## Sarwar Hossain — Core, Payments, Tracking & Admin
- run.py, requirements.txt, .env.example, .vscode/, requests.http, README.md
- app/__init__.py, app/config.py, app/db.py, app/errors.py
- docs/02_W1_Gateway_Legal_Prep.md, docs/04_W2_Architecture_API_Spec.md
- Next: notifications, bKash, trips/GPS, admin, deployment

## Shared rule
Do not edit another person's file without telling them. New routes = new file + one line in app/__init__.py (Sarwar merges).
