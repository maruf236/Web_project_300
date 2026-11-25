// Owner: Ali. Week 1 prototype: draw a route and see the exact data the offer and search APIs need.
import { useState } from 'react'
import { Alert, Button, Card } from '../../shared/ui/index.js'
import RoutePicker from './RoutePicker.jsx'
import { estimateBaseFare } from './routeUtils.js'

export default function MapDemoPage() {
  const [result, setResult] = useState({ route: null, distanceKm: 0 })
  const [copied, setCopied] = useState(false)
  const json = result.route ? JSON.stringify(result.route, null, 2) : ''

  async function copy() {
    try { await navigator.clipboard.writeText(json); setCopied(true); setTimeout(() => setCopied(false), 2000) } catch { /* ignore */ }
  }

  return (
    <div className="grid gap-4 lg:grid-cols-3">
      <Card title="Draw your route" className="lg:col-span-2">
        <p className="mb-3 text-sm text-slate-700">Click the map to set the start, then any stops, then the end. The route follows real roads.</p>
        <RoutePicker onChange={setResult} />
      </Card>
      <Card title="Route details">
        {!result.route ? <p className="text-sm text-slate-600">Pick at least two points to see the distance and fare estimate.</p> : (
          <>
            <dl className="mb-3 space-y-1 text-sm">
              <div className="flex justify-between"><dt>Road distance</dt><dd className="font-semibold">{result.distanceKm.toFixed(2)} km</dd></div>
              <div className="flex justify-between"><dt>Base fare (BDT 10/km)</dt><dd className="font-semibold">BDT {estimateBaseFare(result.distanceKm).toFixed(2)}</dd></div>
            </dl>
            <Alert variant="info">A provider may charge the base fare, less, or zero. The server calculates the final fare.</Alert>
            <label htmlFor="geojson" className="text-sm font-medium">Route data (GeoJSON)</label>
            <textarea id="geojson" readOnly value={json} rows={8} className="mt-1 w-full rounded border border-slate-300 p-2 font-mono text-xs" />
            <Button variant="secondary" onClick={copy} className="mt-2">{copied ? 'Copied' : 'Copy'}</Button>
          </>
        )}
      </Card>
    </div>
  )
}
