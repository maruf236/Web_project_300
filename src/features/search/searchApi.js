// Owner: Ali. POST /api/rides/search -> { count, offers: [{ offerId, provider, origin, destination, departureAt,
// windowMinutes, fareBdt, routeKm, matchPercent, roadDistanceKm }] }
import { post } from '../../shared/api/client.js'
export const searchRides = (body) => post('/api/rides/search', body)
