// Owner: Ali. Backend calls for provider screens (all endpoints exist in the Flask backend).
import { get, patch, post } from '../../shared/api/client.js'
import { geoErrorMessage } from './geo.js'

export const publishOffer = (body) => post('/api/offers', body)              // -> { id, route_length_km, base_fare_bdt, fare_bdt, state, route_version }
export const myOffers = () => get('/api/offers/mine')
export const cancelOffer = (id) => patch(`/api/offers/${id}/cancel`, {})
export const setService = (on) => patch('/api/offers/service', { on })      // -> { serviceOn }
export const shareLocation = ({ lon, lat }) => post('/api/rides/provider-location', { lon, lat })

export const currentPosition = () => new Promise((resolve, reject) => {
  if (!navigator.geolocation) { reject(new Error('Your browser cannot share location.')); return }
  navigator.geolocation.getCurrentPosition(
    (p) => resolve({ lon: p.coords.longitude, lat: p.coords.latitude }),
    (err) => reject(new Error(geoErrorMessage(err.code))),
    { enableHighAccuracy: true, timeout: 10000, maximumAge: 30000 })
})
