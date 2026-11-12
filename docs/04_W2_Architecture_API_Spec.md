# Week 2 — Architecture & API Spec (Owner: Sarwar, with Ali/Tamim)
React+Tailwind SPA -> HTTPS -> Flask REST API -> PostgreSQL/PostGIS. Side services: routing (OSRM), bKash, SMS/email, private object storage.
Layers: routes -> pydantic validation -> SQL (parameterised). Cross-cutting: helmet, rate limit, JWT, RBAC, audit log, error handler.

| Method | Path | Who | Week |
|---|---|---|---|
| POST | /api/auth/register, /verify-email, /login | public | 3 |
| POST | /api/auth/otp/send, /otp/verify | logged in | 3 |
| GET | /api/auth/me | logged in | 3 |
| POST | /api/offers | approved provider | 3 |
| GET | /api/offers/mine | provider | 3 |
| PATCH | /api/offers/service | provider | 3 |
| PATCH | /api/offers/:id/cancel | owner | 3 |
| * | /api/verification/* | user/officer | 4 |
| GET | /api/rides/search | verified student only | 4 |
| POST | /api/bookings, /api/payments/bkash/* | verified student | 5 |
| * | trips, complaints, admin | | 6-7 |

UI map: Auth -> Dashboard -> Verification upload -> Offer manager (route draw, Service ON/OFF) -> Search & book -> Trip -> Admin console (verification, complaints, payments, audit queues).
