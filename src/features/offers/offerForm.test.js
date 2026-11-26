// Owner: Ali. Run: npm test
import test from 'node:test'
import assert from 'node:assert/strict'
import { buildOfferBody, defaultFare, fareLimit, validateOffer, toIso } from './offerForm.js'
import { geoErrorMessage } from './geo.js'

const route = { type: 'LineString', coordinates: [[90.37, 23.74], [90.38, 23.75]] }
const info = { route, distanceKm: 10 }
const now = Date.parse('2026-12-01T00:00:00Z')
const good = { originName: 'Dhanmondi', destinationName: 'Uttara', departureAt: '2026-12-02T08:00', windowMinutes: '15', fare: '90' }

test('valid offer has no errors', () => assert.deepEqual(validateOffer(good, info, now), {}))
test('fare is capped by the BDT 10/km base fare (FR-030, FR-031)', () => {
  assert.equal(defaultFare(10), 100)
  assert.equal(defaultFare(4.567), 45)               // rounded down, so it never exceeds the base fare
  assert.equal(fareLimit(10), 101)                   // 1% tolerance, the server decides
  assert.ok(validateOffer({ ...good, fare: '150' }, info, now).fare)
  assert.deepEqual(validateOffer({ ...good, fare: '0' }, info, now), {})          // zero is allowed
  assert.ok(validateOffer({ ...good, fare: '-1' }, info, now).fare)
  assert.ok(validateOffer({ ...good, fare: '' }, info, now).fare)
})
test('route, names and departure are required', () => {
  const e = validateOffer({ ...good, originName: '', destinationName: 'x', departureAt: '' }, { route: null }, now)
  assert.ok(e.originName && e.destinationName && e.route && e.departureAt)
  assert.ok(validateOffer({ ...good, departureAt: '2020-01-01T08:00' }, info, now).departureAt)   // in the past
})
test('time window 0 to 180 whole minutes', () => {
  for (const w of ['0', '180']) assert.equal(validateOffer({ ...good, windowMinutes: w }, info, now).windowMinutes, undefined)
  for (const w of ['181', '-1', '1.5', 'abc']) assert.ok(validateOffer({ ...good, windowMinutes: w }, info, now).windowMinutes)
})
test('request body matches POST /api/offers', () => {
  const b = buildOfferBody({ ...good, originName: '  Dhanmondi ' }, route)
  assert.equal(b.origin_name, 'Dhanmondi'); assert.equal(b.window_minutes, 15); assert.equal(b.fare_bdt, 90)
  assert.deepEqual(b.route, route); assert.match(b.departure_at, /Z$/)
  assert.equal(new Date(b.departure_at).getTime(), new Date('2026-12-02T08:00').getTime())
  assert.equal(toIso('bad'), null)
})
test('location error messages', () => {
  assert.match(geoErrorMessage(1), /denied/i); assert.match(geoErrorMessage(3), /too long/i); assert.match(geoErrorMessage(99), /could not/i)
})
