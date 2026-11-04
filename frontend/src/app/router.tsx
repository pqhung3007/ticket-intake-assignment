import { lazy } from 'react'
import { createBrowserRouter } from 'react-router'

import { AccountPage, LoginPage, RequireAuth, RequireRole } from '@/features/auth'
import { HomePage } from '@/features/home'

import { RouteErrorBoundary } from './ErrorBoundary'
import { AppShell } from './layouts/AppShell'

// One chunk per feature; pages load on first visit.
const TicketListPage = lazy(() => import('@/features/tickets').then((m) => ({ default: m.TicketListPage })))
const TicketDetailPage = lazy(() =>
  import('@/features/tickets').then((m) => ({ default: m.TicketDetailPage })),
)
const NewTicketPage = lazy(() => import('@/features/tickets').then((m) => ({ default: m.NewTicketPage })))
const RolesPage = lazy(() => import('@/features/users').then((m) => ({ default: m.RolesPage })))
const AboutPage = lazy(() => import('@/features/about').then((m) => ({ default: m.AboutPage })))

export const router = createBrowserRouter([
  { path: 'login', element: <LoginPage />, errorElement: <RouteErrorBoundary /> },
  {
    element: (
      <RequireAuth>
        <AppShell />
      </RequireAuth>
    ),
    errorElement: <RouteErrorBoundary />,
    children: [
      { index: true, element: <HomePage /> },
      { path: 'tickets', element: <TicketListPage /> },
      { path: 'tickets/new', element: <NewTicketPage /> },
      { path: 'tickets/:number', element: <TicketDetailPage /> },
      {
        path: 'admin/roles',
        element: (
          <RequireRole role="admin">
            <RolesPage />
          </RequireRole>
        ),
      },
      { path: 'account', element: <AccountPage /> },
      { path: 'about', element: <AboutPage /> },
      { path: '*', element: <RouteErrorBoundary /> },
    ],
  },
])
