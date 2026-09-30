import { useEffect, useState } from 'react'

import { Badge } from '@/components/ui/badge'
import { getHealth } from '@/lib/api'
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

  useEffect(() => {
    getHealth()
      .then((health) => setApi(health.status === 'ok' ? 'ok' : 'error'))
      .catch(() => setApi('error'))
  }, [])

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <PageTitle>Accueil</PageTitle>
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
