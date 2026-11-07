# RIDEVAI backend — Python Flask + PostgreSQL/PostGIS (Weeks 1-3)

## 1. Install (once)
- Python 3.11+, VS Code (extensions: Python, REST Client)
- PostgreSQL 16 + PostGIS (Windows: EDB installer, then Stack Builder -> Spatial Extensions -> PostGIS. Mac: `brew install postgresql@16 postgis`. Ubuntu: `sudo apt install postgresql postgresql-16-postgis-3`)

## 2. Create the database (once per teammate)
```
psql -U postgres -c "CREATE DATABASE ridevai;"
psql -U postgres -d ridevai -f db/schema.sql
```
Windows full path if psql is not found: `& "C:\Program Files\PostgreSQL\16\bin\psql.exe" -U postgres ...`
If you change `db/schema.sql` later, drop and recreate the database (`DROP DATABASE ridevai;`) and reload it, then tell the team.

## 3. Run the backend
```
python -m venv .venv
.venv\Scripts\activate            # Mac/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env            # Mac/Linux: cp .env.example .env
```
Edit `.env`: `DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/ridevai`, and set a long random `JWT_SECRET`.
```
python run.py
```
Open http://localhost:4000/health -> `{"ok": true}`.

## 4. Test
Open `requests.http` in VS Code (REST Client) and click "Send Request" on each block. Email tokens and OTP codes print in the terminal (stub senders; real email/SMS comes later).

## Notes
- This is an API only; the React frontend comes next.
- To test offers before Week 4, set `users.identity_status='verified'`, add a `rider_profiles` row (`rider_status='verified'`) and a `vehicles` row by hand.
- Who edits what: see OWNERSHIP.md. Git branches: `tamim-auth`, `ali-routing`, `sarwar-core`.
