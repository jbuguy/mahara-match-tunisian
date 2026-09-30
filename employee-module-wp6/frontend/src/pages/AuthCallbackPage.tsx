import { useEffect, useState } from 'react'
import { Link, Navigate } from 'react-router'

import { FullPageMessage } from '@/components/auth/FullPageMessage'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/lib/auth-context'
import { supabase } from '@/lib/supabase'

/** supabase-js swallows callback errors (and says nothing if the PKCE verifier is missing), so find out why. */
async function failureReason(): Promise<string> {
  const { error } = await supabase.auth.initialize()
  if (error) return error.message
  const params = new URLSearchParams(window.location.search)
  const errorDescription = params.get('error_description')
  if (errorDescription) return errorDescription
  if (!params.has('code')) return 'no ?code= in the callback URL'
  return 'PKCE code verifier not found in this browser (sign-in started on another address or tab?)'
}

/** Google sends the user back here; supabase-js exchanges the ?code= for a session, then we go to Accueil. */
export function AuthCallbackPage() {
  const { session, loading } = useAuth()
  const [reason, setReason] = useState<string | null>(null)
  const failed = !loading && !session

  useEffect(() => {
    if (!failed) return
    failureReason().then((text) => {
      console.error('[auth callback]', text)
      setReason(text)
    })
  }, [failed])

  if (session) return <Navigate to="/" replace />
  if (loading) return <FullPageMessage>Connexion en cours…</FullPageMessage>

  return (
    <FullPageMessage spinner={false}>
      <p role="alert" className="text-danger">
        La connexion a échoué.
      </p>
      {reason && <p className="max-w-sm text-[13px] text-ink-secondary">Détail : {reason}</p>}
      <Button asChild variant="outline">
        <Link to="/login" replace>
          Réessayer
        </Link>
      </Button>
    </FullPageMessage>
  )
}
