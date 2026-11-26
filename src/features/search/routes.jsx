// Owner: Ali. Student search screens (professionals cannot search or book).
import { RequireContactVerified, RequireRole } from '../../shared/auth/guards.jsx'
import { isStudent } from '../../shared/roles.js'
import SearchPage from './SearchPage.jsx'

export const searchRoutes = [
  { path: '/search', element: <RequireRole categories={['student']}><RequireContactVerified><SearchPage /></RequireContactVerified></RequireRole> },
]
export const searchNav = [{ to: '/search', label: 'Find a ride', visible: isStudent }]
