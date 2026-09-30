import { Navigate, Outlet } from 'react-router'

import { useAuth } from '@/lib/auth-context'
import { FullPageMessage } from './FullPageMessage'

/** Wraps every page except /login and /auth/callback: signed-out users go to /login. */
export function RequireAuth() {
  const { session, loading } = useAuth()
  if (loading) return <FullPageMessage>Chargement…</FullPageMessage>
  if (!session) return <Navigate to="/login" replace />
  return <Outlet />
}
