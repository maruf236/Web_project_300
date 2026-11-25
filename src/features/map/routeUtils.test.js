// Owner: Ali. Run: npm test
import test from 'node:test'
import assert from 'node:assert/strict'
import { haversineKm, pathLengthKm, estimateBaseFare, isInsideBangladesh, validateRoute, thinCoordinates, toLineString } from './routeUtils.js'

test('base fare is BDT 10 per km, rounded to 2 decimals', () => {
  assert.equal(estimateBaseFare(10), 100)
  assert.equal(estimateBaseFare(4.567), 45.67)
  assert.equal(estimateBaseFare(0), 0)
})

test('haversine: one degree of latitude is about 111 km', () => {
  const km = haversineKm([90, 23], [90, 24])
  assert.ok(km > 110.5 && km < 111.8)
})

test('path length adds up the segments', () => {
  const a = [90.37, 23.74], b = [90.38, 23.75], c = [90.39, 23.76]
  assert.ok(Math.abs(pathLengthKm([a, b, c]) - (haversineKm(a, b) + haversineKm(b, c))) < 1e-9)
})

test('Bangladesh bounds match the backend box', () => {
  assert.equal(isInsideBangladesh([90.4, 23.8]), true)
  assert.equal(isInsideBangladesh([77.2, 28.6]), false)   // Delhi
  assert.equal(isInsideBangladesh([88, 20.5]), true)
})

test('route validation', () => {
  assert.equal(validateRoute([[90.37, 23.74], [90.38, 23.75]]).ok, true)
  assert.equal(validateRoute([[90.37, 23.74]]).ok, false)
  assert.equal(validateRoute([[90.37, 23.74], [77.2, 28.6]]).ok, false)
  assert.equal(validateRoute([[90.37, 23.74], [90.37, 23.74]]).ok, false)
  assert.equal(validateRoute([[90.37, 'x'], [90.38, 23.75]]).ok, false)
})

test('thinning keeps first and last point and respects the limit', () => {
  const pts = Array.from({ length: 10000 }, (_, i) => [90 + i * 1e-5, 23 + i * 1e-5])
  const out = thinCoordinates(pts, 4000)
  assert.equal(out.length, 4000)
  assert.deepEqual(out[0], pts[0])
  assert.deepEqual(out[out.length - 1], pts[pts.length - 1])
  assert.equal(thinCoordinates(pts.slice(0, 10), 4000).length, 10)
})

test('GeoJSON shape matches the API', () => {
  assert.deepEqual(toLineString([[1, 2], [3, 4]]), { type: 'LineString', coordinates: [[1, 2], [3, 4]] })
})
