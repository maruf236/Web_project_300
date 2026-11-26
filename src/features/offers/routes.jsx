// Owner: Ali. Provider screens.
import { RequireContactVerified } from '../../shared/auth/guards.jsx'
import PublishOfferPage from './PublishOfferPage.jsx'
import MyOffersPage from './MyOffersPage.jsx'

const verified = (el) => <RequireContactVerified>{el}</RequireContactVerified>
export const offersRoutes = [
  { path: '/offers', element: verified(<MyOffersPage />) },
  { path: '/offers/new', element: verified(<PublishOfferPage />) },
]
export const offersNav = [
  { to: '/offers', label: 'My offers', visible: (u) => !!u },
  { to: '/offers/new', label: 'Publish offer', visible: (u) => !!u },
]
