// Owner: Ali. Run: npm test
import test from 'node:test'
import assert from 'node:assert/strict'
import { buildSearchBody, defaultWindow, toLocalInput, validateSearch } from './searchForm.js'

const route = { type: 'LineString', coordinates: [[90.37, 23.74], [90.38, 23.75]] }
const info = { route }
const v = { departAfter: '2026-12-01T06:00', departBefore: '2026-12-01T10:00' }

test('valid search has no errors', () => assert.deepEqual(validateSearch(v, info), {}))
test('a route and a sensible time window are required', () => {
  assert.ok(validateSearch(v, { route: null }).route)
  assert.ok(validateSearch({ departAfter: '2026-12-01T10:00', departBefore: '2026-12-01T06:00' }, info).departBefore)
  assert.ok(validateSearch({ departAfter: '2026-12-01T06:00', departBefore: '2026-12-04T06:00' }, info).departBefore)   // over 48 hours
  assert.ok(validateSearch({ departAfter: '', departBefore: '' }, info).departAfter)
})
test('exactly 48 hours is allowed', () => assert.deepEqual(validateSearch({ departAfter: '2026-12-01T06:00', departBefore: '2026-12-03T06:00' }, info), {}))
test('request body matches POST /api/rides/search', () => {
  const b = buildSearchBody(v, route)
  assert.deepEqual(b.route, route); assert.equal(b.limit, 20)
  assert.match(b.depart_after, /Z$/); assert.ok(new Date(b.depart_before) > new Date(b.depart_after))
})
test('default window starts in 30 minutes and lasts a few hours', () => {
  const now = new Date('2026-12-01T10:00:00')
  const w = defaultWindow(now)
  assert.equal(w.departAfter, toLocalInput(new Date(now.getTime() + 30 * 60000)))
  assert.ok(new Date(w.departBefore) - new Date(w.departAfter) === 3.5 * 3600000)
})
