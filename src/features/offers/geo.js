// Owner: Ali. Friendly text for browser location errors.
export function geoErrorMessage(code) {
  if (code === 1) return 'Location permission was denied. Allow location access in your browser settings.'
  if (code === 2) return 'Your location is not available right now.'
  if (code === 3) return 'Finding your location took too long. Try again.'
  return 'Could not get your location.'
}
