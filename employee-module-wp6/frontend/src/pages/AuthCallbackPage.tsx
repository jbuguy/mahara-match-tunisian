import { Link, Navigate } from 'react-router'

import { FullPageMessage } from '@/components/auth/FullPageMessage'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/lib/auth-context'

/** The backend consumes Google's callback and returns a Mahara token in the URL fragment. */
export function AuthCallbackPage() {
  const { session, loading } = useAuth()
  const failed = !loading && !session
  const reason = new URLSearchParams(window.location.search).get('error')

  if (session) return <Navigate to="/" replace />
  if (loading) return <FullPageMessage>Connexion en cours…</FullPageMessage>

  return (
    <FullPageMessage spinner={false}>
      <p role="alert" className="text-danger">
        La connexion a échoué.
      </p>
      {failed && <p className="max-w-sm text-[13px] text-ink-secondary">Détail : {reason ?? 'Aucune session reçue.'}</p>}
      <Button asChild variant="outline">
        <Link to="/login" replace>
          Réessayer
        </Link>
      </Button>
    </FullPageMessage>
  )
}
