# Frontend Week 2 - Ali (A3 to A6, plus A7 results)
All screens use endpoints that already exist in the Flask backend.

| Task | Screen | Path | Endpoint |
|---|---|---|---|
| A3 | Service ON/OFF + location sharing (panel on My offers) | `/offers` | `PATCH /api/offers/service`, `POST /api/rides/provider-location` |
| A4 | Publish offer (map route, time, window, fare) | `/offers/new` | `POST /api/offers` |
| A5 | My offers + cancel with confirmation | `/offers` | `GET /api/offers/mine`, `PATCH /api/offers/<id>/cancel` |
| A6 | Ride search form (route, earliest and latest departure) | `/search` | `POST /api/rides/search` |
| A7 | Results list: match %, road distance, fare, provider first name | `/search` | same |

## Rules shown in the UI
- Fare: BDT 10 per km shown as a hint; the provider may charge less or 0 (FR-030, FR-031). The default fare is rounded down so it never exceeds the base. The server still rejects a higher fare and the message is shown.
- Time window 0-180 minutes; departure must be in the future; search window at most 48 hours.
- Search is for students only (professionals are blocked in the UI and by the backend). Backend codes such as `PROVIDER_NOT_APPROVED` or `IDENTITY_UNVERIFIED` become plain messages.
- Location is shared only while Service is ON, once on request or every minute while the page is open (FR-015).
- The Book button is disabled until the booking screen (A8) is built in Week 3.

## Files
`offers/`: `offerForm.js`, `geo.js`, `offersApi.js`, `ServicePanel.jsx`, `PublishOfferPage.jsx`, `MyOffersPage.jsx`, `routes.jsx`. `search/`: `searchForm.js`, `searchApi.js`, `SearchPage.jsx`, `routes.jsx`. `map/routes.jsx` now also gathers the two route lists. Tests: `offerForm.test.js` (6), `searchForm.test.js` (5).

## Backend gaps found
1. No endpoint tells the frontend the current Service ON/OFF state or whether the provider is approved. The panel shows "not set in this session" until you press a button. Suggest adding `serviceOn` and `riderStatus` to `/api/auth/me`.
2. Cancelling an offer does not cancel its live bookings (Week 3 backend behaviour).
3. The search result has no `routeVersion`; the booking screen will not need it.

## Next (Week 3)
A8 booking preview + confirm with the 10-minute seat-hold timer, A9 my bookings and cancel with reason.
