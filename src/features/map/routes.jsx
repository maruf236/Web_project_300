// Owner: Ali. Add your screens here only; App.jsx (Sarwar) picks these arrays up.
import MapDemoPage from './MapDemoPage.jsx'

export const mapRoutes = [
  { path: '/map-demo', element: <MapDemoPage /> },
]

export const mapNav = [
  { to: '/map-demo', label: 'Map demo' },
]
