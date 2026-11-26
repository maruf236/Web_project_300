import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Alert, Button, Card, TextField, useToast } from '../../shared/ui/index.js'
import { friendlyError } from '../../shared/errors.js'
import { formatBdt } from '../../shared/format.js'
import RoutePicker from '../map/RoutePicker.jsx'
import { estimateBaseFare } from '../map/routeUtils.js'
import { buildOfferBody, defaultFare, validateOffer } from './offerForm.js'
import { publishOffer } from './offersApi.js'

export default function PublishOfferPage() {
  const navigate = useNavigate()
  const toast = useToast()
  const [v, setV] = useState({ originName: '', destinationName: '', departureAt: '', windowMinutes: '15', fare: '' })
  const [fareTouched, setFareTouched] = useState(false)
  const [routeInfo, setRouteInfo] = useState({ route: null, distanceKm: 0 })
  const [errors, setErrors] = useState({})
  const [formError, setFormError] = useState('')
  const [busy, setBusy] = useState(false)
  const set = (k) => (e) => setV((s) => ({ ...s, [k]: e.target.value }))

  function onRoute(info) {
    setRouteInfo(info)
    if (info.route && !fareTouched) setV((s) => ({ ...s, fare: String(defaultFare(info.distanceKm)) }))
  }

  async function submit(ev) {
    ev.preventDefault()
    setFormError('')
    const errs = validateOffer(v, routeInfo)
    setErrors(errs)
    if (Object.keys(errs).length) return
    setBusy(true)
    try { await publishOffer(buildOfferBody(v, routeInfo.route)); toast('Your offer is published.', 'success'); navigate('/offers') }
    catch (e) { setFormError(friendlyError(e)) }
    finally { setBusy(false) }
  }

  const base = routeInfo.route ? estimateBaseFare(routeInfo.distanceKm) : null
  return (
    <div className="grid gap-4 lg:grid-cols-5">
      <Card title="1. Your route" className="lg:col-span-3">
        <p className="mb-3 text-sm text-slate-700">Offer a trip you already plan to make. The route cannot be changed after students book it.</p>
        <RoutePicker onChange={onRoute} />
        {errors.route && <Alert variant="error">{errors.route}</Alert>}
      </Card>
      <Card title="2. Trip details" className="lg:col-span-2">
        {formError && <Alert variant="error">{formError}</Alert>}
        <form onSubmit={submit} noValidate>
          <TextField label="From (place name)" required value={v.originName} onChange={set('originName')} error={errors.originName} />
          <TextField label="To (place name)" required value={v.destinationName} onChange={set('destinationName')} error={errors.destinationName} />
          <TextField label="Departure" required type="datetime-local" value={v.departureAt} onChange={set('departureAt')} error={errors.departureAt} />
          <TextField label="Flexible time window (minutes)" type="number" min="0" max="180" value={v.windowMinutes} onChange={set('windowMinutes')} error={errors.windowMinutes} hint="0 to 180" />
          <TextField label="Fare for the passenger (BDT)" required type="number" min="0" step="0.01" value={v.fare}
            onChange={(e) => { setFareTouched(true); set('fare')(e) }} error={errors.fare}
            hint={base === null ? 'Draw a route to see the base fare' : `Base fare is about ${formatBdt(base)} (BDT 10 per km). You may charge less, or 0.`} />
          <p className="mb-3 text-xs text-slate-600">One passenger seat. Payment is by bKash only. The server calculates the final base fare and rejects a higher fare.</p>
          <Button type="submit" loading={busy} className="w-full">Publish offer</Button>
        </form>
      </Card>
    </div>
  )
}
