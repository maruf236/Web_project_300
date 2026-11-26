// Service ON/OFF and location sharing (FR-011, FR-014, FR-015). Location is only sent while Service is ON.
import { useEffect, useRef, useState } from 'react'
import { Alert, Button, Card } from '../../shared/ui/index.js'
import { friendlyError } from '../../shared/errors.js'
import { currentPosition, setService, shareLocation } from './offersApi.js'

const EVERY_MS = 60000

export default function ServicePanel() {
  const [on, setOn] = useState(null) // null = unknown: the backend has no "read" endpoint yet, so it is only known after you set it here
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState(null)
  const [keep, setKeep] = useState(false)
  const sharing = useRef(false)

  async function toggle(next) {
    setBusy(true); setMsg(null)
    try { const r = await setService(next); setOn(r.serviceOn); if (!r.serviceOn) setKeep(false) }
    catch (e) { setMsg({ v: 'error', t: friendlyError(e) }) }
    finally { setBusy(false) }
  }

  async function share(quiet) {
    if (sharing.current) return
    sharing.current = true
    try { await shareLocation(await currentPosition()); if (!quiet) setMsg({ v: 'success', t: 'Your location was shared.' }) }
    catch (e) { setMsg({ v: 'error', t: friendlyError(e) }); setKeep(false) }
    finally { sharing.current = false }
  }

  useEffect(() => {
    if (!keep || !on) return
    share(true)
    const t = setInterval(() => share(true), EVERY_MS)
    return () => clearInterval(t)
  }, [keep, on]) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <Card title="Service ON/OFF">
      <p className="mb-2 text-sm">Status: <strong>{on === null ? 'not set in this session' : on ? 'ON (students can find your offers)' : 'OFF (your offers are hidden)'}</strong></p>
      <div className="mb-3 flex flex-wrap gap-2">
        <Button onClick={() => toggle(true)} loading={busy} disabled={on === true}>Turn Service ON</Button>
        <Button variant="secondary" onClick={() => toggle(false)} loading={busy} disabled={on === false}>Turn Service OFF</Button>
      </div>
      {msg && <Alert variant={msg.v}>{msg.t}</Alert>}
      {on && (
        <div className="space-y-2 text-sm">
          <Button variant="secondary" onClick={() => share(false)}>Share my location now</Button>
          <label className="flex items-center gap-2"><input type="checkbox" checked={keep} onChange={(e) => setKeep(e.target.checked)} /> Keep sharing every minute while this page is open</label>
          <p className="text-xs text-slate-600">Your location is used only to decide whether you are far enough from a student by road. It is never shown to other users.</p>
        </div>
      )}
      {on === false && <p className="text-xs text-slate-600">Location sharing stops while Service is OFF.</p>}
    </Card>
  )
}
