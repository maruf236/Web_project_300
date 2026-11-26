import { useState } from 'react'
import { Alert, Button, Card, TextField } from '../../shared/ui/index.js'
import { friendlyError } from '../../shared/errors.js'
import { formatBdt, formatDateTime } from '../../shared/format.js'
import RoutePicker from '../map/RoutePicker.jsx'
import { buildSearchBody, defaultWindow, validateSearch } from './searchForm.js'
import { searchRides } from './searchApi.js'

export default function SearchPage() {
  const [v, setV] = useState(defaultWindow())
  const [routeInfo, setRouteInfo] = useState({ route: null })
  const [errors, setErrors] = useState({})
  const [formError, setFormError] = useState('')
  const [busy, setBusy] = useState(false)
  const [results, setResults] = useState(null)

  async function submit(ev) {
    ev.preventDefault()
    setFormError(''); setResults(null)
    const errs = validateSearch(v, routeInfo)
    setErrors(errs)
    if (Object.keys(errs).length) return
    setBusy(true)
    try { setResults((await searchRides(buildSearchBody(v, routeInfo.route))).offers) }
    catch (e) { setFormError(friendlyError(e)) }
    finally { setBusy(false) }
  }

  return (
    <div className="space-y-4">
      <div className="grid gap-4 lg:grid-cols-5">
        <Card title="1. Your route" className="lg:col-span-3">
          <p className="mb-3 text-sm text-slate-700">Click your pickup point first, then your stops, then your destination.</p>
          <RoutePicker onChange={setRouteInfo} />
          {errors.route && <Alert variant="error">{errors.route}</Alert>}
        </Card>
        <Card title="2. When do you want to leave?" className="lg:col-span-2">
          {formError && <Alert variant="error">{formError}</Alert>}
          <form onSubmit={submit} noValidate>
            <TextField label="Earliest departure" required type="datetime-local" value={v.departAfter} onChange={(e) => setV({ ...v, departAfter: e.target.value })} error={errors.departAfter} />
            <TextField label="Latest departure" required type="datetime-local" value={v.departBefore} onChange={(e) => setV({ ...v, departBefore: e.target.value })} error={errors.departBefore} />
            <p className="mb-3 text-xs text-slate-600">Only rides whose route fully covers yours are shown.</p>
            <Button type="submit" loading={busy} className="w-full">Find rides</Button>
          </form>
        </Card>
      </div>
      {results && (
        <Card title={`Rides found: ${results.length}`}>
          {results.length === 0 && <p className="text-sm text-slate-600">No rides match your route and time. Try a wider time window or a shorter route.</p>}
          <ul className="space-y-3">
            {results.map((o) => (
              <li key={o.offerId} className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-slate-200 p-3 text-sm">
                <div>
                  <p className="font-semibold">{o.origin} to {o.destination}</p>
                  <p>{formatDateTime(o.departureAt)} (flexible by {o.windowMinutes} min) | Provider: {o.provider}</p>
                  <p className="text-slate-600">Route match {o.matchPercent}% | Provider is {o.roadDistanceKm} km away by road | Trip {Number(o.routeKm).toFixed(1)} km</p>
                </div>
                <div className="text-right">
                  <p className="text-base font-semibold">{formatBdt(o.fareBdt)}</p>
                  <Button disabled title="The booking screen arrives in Week 3" className="mt-1">Book (next step)</Button>
                </div>
              </li>
            ))}
          </ul>
        </Card>
      )}
    </div>
  )
}
