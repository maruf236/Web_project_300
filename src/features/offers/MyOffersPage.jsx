import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Alert, Button, Card, DataTable, FullPageSpinner, Modal, useToast } from '../../shared/ui/index.js'
import { useApi } from '../../shared/hooks.js'
import { formatBdt, formatDateTime, titleCase } from '../../shared/format.js'
import { friendlyError } from '../../shared/errors.js'
import ServicePanel from './ServicePanel.jsx'
import { cancelOffer, myOffers } from './offersApi.js'

export default function MyOffersPage() {
  const { data, error, loading, reload } = useApi(myOffers, [])
  const toast = useToast()
  const [target, setTarget] = useState(null)
  const [busy, setBusy] = useState(false)

  async function confirmCancel() {
    setBusy(true)
    try { await cancelOffer(target.id); toast('Offer cancelled.', 'success'); setTarget(null); reload() }
    catch (e) { toast(friendlyError(e), 'error'); setTarget(null) }
    finally { setBusy(false) }
  }

  const columns = [
    { key: 'trip', header: 'Trip', render: (o) => `${o.origin_name} to ${o.destination_name}` },
    { key: 'departure_at', header: 'Departure', render: (o) => formatDateTime(o.departure_at) },
    { key: 'route_length_km', header: 'Distance', render: (o) => `${Number(o.route_length_km).toFixed(1)} km` },
    { key: 'fare_bdt', header: 'Fare', render: (o) => formatBdt(o.fare_bdt) },
    { key: 'state', header: 'Status', render: (o) => titleCase(o.state) },
    { key: 'actions', header: '', render: (o) => o.state === 'published' ? <Button variant="danger" className="!py-1" onClick={() => setTarget(o)}>Cancel</Button> : null },
  ]
  return (
    <div className="space-y-4">
      <ServicePanel />
      <Card title="My ride offers">
        <p className="mb-3"><Link className="text-sm text-brand underline" to="/offers/new">Publish a new offer</Link></p>
        {loading && <FullPageSpinner />}
        {error && <Alert variant="error">{friendlyError(error)}</Alert>}
        {data && <DataTable columns={columns} rows={data} empty="You have not published any offers yet." />}
      </Card>
      <Modal open={!!target} title="Cancel this offer?" onClose={() => setTarget(null)}>
        <p className="mb-4 text-sm">{target && `${target.origin_name} to ${target.destination_name}, ${formatDateTime(target.departure_at)}`}. Students will no longer be able to find or book it.</p>
        <div className="flex gap-2"><Button variant="danger" loading={busy} onClick={confirmCancel}>Yes, cancel offer</Button><Button variant="secondary" onClick={() => setTarget(null)}>Keep it</Button></div>
      </Modal>
    </div>
  )
}
