// Owner: Ali. This file also gathers Ali's other folders (offers, search), so App.jsx (Sarwar) never has to change.
import MapDemoPage from './MapDemoPage.jsx'
import { offersRoutes, offersNav } from '../offers/routes.jsx'
import { searchRoutes, searchNav } from '../search/routes.jsx'

export const mapRoutes = [
  { path: '/map-demo', element: <MapDemoPage /> },   // Week 1 prototype (not in the menu)
  ...offersRoutes, ...searchRoutes,
]
export const mapNav = [...searchNav, ...offersNav]
