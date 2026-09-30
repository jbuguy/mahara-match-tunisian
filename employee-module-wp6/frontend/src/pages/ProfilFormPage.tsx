import { useCallback, useEffect, useState } from 'react'
import { useLocation, useNavigate } from 'react-router'

import { ProfileForm } from '@/components/profile/ProfileForm'
import { profileToFormValues } from '@/components/profile/form-values'
import { Button } from '@/components/ui/button'
import { getProfile, type Profile } from '@/lib/api'
import { useAuth } from '@/lib/auth-context'
import { PageTitle } from './placeholders'

type State = { status: 'loading' } | { status: 'error' } | { status: 'ready'; profile: Profile | null }

/**
 * Create or edit the profile: prefilled with the saved profile, or with the Google name for a new one.
 * The Profil page hands over the profile it already has (`state.profile`, null = none yet); a direct visit loads it.
 */
export function ProfilFormPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { session } = useAuth()
  const handedOver: { profile: Profile | null } | null =
    location.state && 'profile' in location.state ? location.state : null
  const [state, setState] = useState<State>(() =>
    handedOver ? { status: 'ready', profile: handedOver.profile } : { status: 'loading' },
  )

  const load = useCallback(() => {
    let ignore = false
    getProfile()
      .then((profile) => {
        if (!ignore) setState({ status: 'ready', profile })
      })
      .catch(() => {
        if (!ignore) setState({ status: 'error' })
      })
    return () => {
      ignore = true
    }
  }, [])

  // Load once on arrival, unless the Profil page handed the profile over.
  const [needsLoad] = useState(!handedOver)
  useEffect(() => (needsLoad ? load() : undefined), [load, needsLoad])

  if (state.status === 'loading') {
    return (
      <section className="space-y-4">
        <PageTitle>Mon profil</PageTitle>
        <p role="status" className="text-ink-secondary">Chargement du profil…</p>
      </section>
    )
  }
  if (state.status === 'error') {
    return (
      <section className="space-y-4">
        <PageTitle>Mon profil</PageTitle>
        <div role="alert" className="space-y-3 rounded-[10px] border bg-surface p-5">
          <p className="text-danger">Impossible de charger votre profil.</p>
          <Button
            variant="outline"
            onClick={() => {
              setState({ status: 'loading' })
              load()
            }}
          >
            Réessayer
          </Button>
        </div>
      </section>
    )
  }

  const { profile } = state
  const metadata = session?.user.user_metadata ?? {}
  // The form reads its starting values once, when it first renders.
  const start = profile ? profileToFormValues(profile) : { full_name: metadata.full_name || metadata.name || '' }

  return (
    <section className="space-y-5">
      <div className="mx-auto max-w-2xl">
        <PageTitle>{profile ? 'Modifier mon profil' : 'Créer mon profil'}</PageTitle>
      </div>
      <ProfileForm
        initialValues={start}
        onSaved={(saved, { photoFailed }) =>
          navigate('/profil', { state: { saved: true, profile: saved, photoFailed } })
        }
      />
    </section>
  )
}
