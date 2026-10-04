import { useEffect, useState } from 'react'

import { Badge } from '@/components/ui/badge'
import { getHealth, getMe } from '@/lib/api'
import { displayName, useAuth } from '@/lib/auth-context'
import { cn } from '@/lib/utils'
import { PageTitle } from './placeholders'

type ApiState = 'loading' | 'ok' | 'error'

const BADGE_TEXT: Record<ApiState, string> = {
  loading: 'API : …',
  ok: 'API : ok',
  error: 'API : erreur',
}

export function AccueilPage() {
  const [api, setApi] = useState<ApiState>('loading')
  const { session } = useAuth()

  useEffect(() => {
    getHealth()
      .then((health) => setApi(health.status === 'ok' ? 'ok' : 'error'))
      .catch(() => setApi('error'))
    // Also creates our users row on first login; a 401 here signs the user out (see lib/api.ts).
    getMe().catch(() => {})
  }, [])

  // The name is already in the Supabase session, so the greeting doesn't wait for the backend.
  const firstName = session?.user.user_metadata.full_name?.split(' ')[0] ?? displayName(session).split('@')[0]

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <PageTitle>{firstName ? `Bonjour ${firstName}` : 'Accueil'}</PageTitle>
        <Badge
          role="status"
          className={cn(
            'h-6 rounded-full px-3 text-[13px]',
            api === 'ok' && 'bg-teal text-white',
            api === 'error' && 'bg-danger text-white',
            api === 'loading' && 'bg-muted text-ink-secondary',
          )}
        >
          {BADGE_TEXT[api]}
        </Badge>
      </div>
      <p className="text-ink-secondary">Bienvenue sur Mahara, votre espace pour trouver un emploi.</p>
    </section>
  )
}
