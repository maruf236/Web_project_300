// Owner: Ali. Pure rules for the publish-offer form (no React). The BACKEND is the final judge of every rule.
import { estimateBaseFare } from '../map/routeUtils.js'

export const MAX_WINDOW_MINUTES = 180
// The frontend only estimates the distance, so allow 1% extra before blocking; the server shows the exact limit.
export const fareLimit = (km) => Math.ceil(estimateBaseFare(km) * 1.01 * 100) / 100
export const defaultFare = (km) => Math.max(0, Math.floor(estimateBaseFare(km)))

export function toIso(localValue) {
  const d = new Date(localValue)
  return Number.isNaN(d.getTime()) ? null : d.toISOString()
}

export function validateOffer(v, routeInfo, now = Date.now()) {
  const e = {}
  if (!v.originName || v.originName.trim().length < 2) e.originName = 'Enter the starting place (at least 2 characters).'
  if (!v.destinationName || v.destinationName.trim().length < 2) e.destinationName = 'Enter the destination (at least 2 characters).'
  if (!routeInfo?.route) e.route = 'Draw your route on the map first.'
  const dep = v.departureAt ? new Date(v.departureAt).getTime() : NaN
  if (Number.isNaN(dep)) e.departureAt = 'Choose the departure date and time.'
  else if (dep <= now) e.departureAt = 'Departure must be in the future.'
  const w = Number(v.windowMinutes)
  if (!Number.isInteger(w) || w < 0 || w > MAX_WINDOW_MINUTES) e.windowMinutes = `Time window must be a whole number from 0 to ${MAX_WINDOW_MINUTES} minutes.`
  const fare = Number(v.fare)
  if (v.fare === '' || !Number.isFinite(fare) || fare < 0) e.fare = 'Enter a fare of 0 or more.'
  else if (routeInfo?.route && fare > fareLimit(routeInfo.distanceKm)) e.fare = `Fare cannot be more than the base fare (about BDT ${estimateBaseFare(routeInfo.distanceKm).toFixed(2)}).`
  return e
}

export const buildOfferBody = (v, route) => ({
  origin_name: v.originName.trim(),
  destination_name: v.destinationName.trim(),
  route,
  departure_at: toIso(v.departureAt),
  window_minutes: Number(v.windowMinutes || 0),
  fare_bdt: Number(v.fare),
})
