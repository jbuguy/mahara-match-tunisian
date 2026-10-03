import { ClipboardCheck, MessageCircle } from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'
import { flushSync } from 'react-dom'
import { useLocation, useNavigate } from 'react-router'

import { AssistantChat } from '@/components/assistant/AssistantChat'
import { useAssistantChat } from '@/components/assistant/use-assistant-chat'
import { ProfileForm, type ProfileFormHandle } from '@/components/profile/ProfileForm'
import { profileToFormValues } from '@/components/profile/form-values'
import { Button } from '@/components/ui/button'
import { Sheet, SheetContent, SheetDescription, SheetTitle } from '@/components/ui/sheet'
import { getProfile, type Profile } from '@/lib/api'
import { useAuth } from '@/lib/auth-context'
import { useMediaQuery } from '@/lib/use-media-query'
import { cn } from '@/lib/utils'
import { PageTitle } from './placeholders'

type State = { status: 'loading' } | { status: 'error' } | { status: 'ready'; profile: Profile | null }

/** From this width the assistant sits next to the form, so both stay visible; below it opens as a bottom sheet. */
const SIDE_PANEL = '(min-width: 1280px)'

/**
 * Create or edit the profile: prefilled with the saved profile, or with the Google name for a new one.
 * The Profil page hands over the profile it already has (`state.profile`, null = none yet); a direct visit loads it.
 * `state.assistant` opens the profile assistant right away. It fills the form; the candidate saves.
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

  const formRef = useRef<ProfileFormHandle>(null)
  const chat = useAssistantChat(formRef)
  const sidePanel = useMediaQuery(SIDE_PANEL)
  const [assistantOpen, setAssistantOpen] = useState(() => Boolean(location.state?.assistant))
  const [reviewing, setReviewing] = useState(false)
  const openButtonRef = useRef<HTMLButtonElement>(null)
  const reviewNoticeRef = useRef<HTMLParagraphElement>(null)
  const reviewAfterClose = useRef(false)

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
  const panelShown = assistantOpen && sidePanel

  function closePanel() {
    // The panel's close button disappears: give focus back to the button that opens it.
    flushSync(() => setAssistantOpen(false))
    openButtonRef.current?.focus()
  }

  /** Focus the form and show the "Vérifiez vos informations" notice just above it. */
  function showForm() {
    formRef.current?.focusForm()
    reviewNoticeRef.current?.scrollIntoView({ block: 'start' })
  }

  /** "Vérifier mon profil": close the chat and bring the form into view. */
  function review() {
    if (!sidePanel) {
      reviewAfterClose.current = true // done once the sheet has closed (see onCloseAutoFocus)
      setReviewing(true)
      setAssistantOpen(false)
      return
    }
    flushSync(() => {
      setReviewing(true)
      setAssistantOpen(false)
    })
    showForm()
  }

  return (
    <section className={cn('space-y-5', panelShown && 'grid grid-cols-[minmax(0,1fr)_22.5rem] items-start gap-6 space-y-0')}>
      <div className="min-w-0 space-y-5">
        <div className="mx-auto max-w-2xl space-y-4">
          <PageTitle>{profile ? 'Modifier mon profil' : 'Créer mon profil'}</PageTitle>
          {!panelShown && (
            <Button
              ref={openButtonRef}
              variant="outline"
              size="lg"
              className="w-full sm:w-auto"
              onClick={() => setAssistantOpen(true)}
            >
              <MessageCircle aria-hidden />
              Remplir avec l'assistant
            </Button>
          )}
          {reviewing && !assistantOpen && (
            <p
              ref={reviewNoticeRef}
              role="status"
              className="flex scroll-mt-20 items-start gap-2 rounded-[10px] border border-gold/60 bg-gold/10 p-4 text-ink lg:scroll-mt-24"
            >
              <ClipboardCheck aria-hidden className="mt-0.5 size-5 shrink-0 text-teal" />
              Vérifiez vos informations. À l'étape 3, cochez la case puis appuyez sur « Enregistrer ».
            </p>
          )}
        </div>
        <ProfileForm
          ref={formRef}
          initialValues={start}
          onSaved={(saved, { photoFailed }) =>
            navigate('/profil', { state: { saved: true, profile: saved, photoFailed } })
          }
        />
      </div>

      {panelShown && (
        <aside
          aria-label="Assistant Mahara"
          className="sticky top-24 h-[calc(100dvh-8.5rem)] overflow-hidden rounded-[10px] border bg-surface"
        >
          <AssistantChat chat={chat} onClose={closePanel} onReview={review} autoFocus />
        </aside>
      )}

      {!sidePanel && (
        <Sheet open={assistantOpen} onOpenChange={setAssistantOpen}>
          <SheetContent
            side="bottom"
            showCloseButton={false}
            className="h-[85dvh] gap-0 overflow-hidden rounded-t-2xl p-0 outline-none"
            // Don't open the phone keyboard right away: let the candidate read the question first.
            onOpenAutoFocus={(event) => {
              event.preventDefault()
              ;(event.target as HTMLElement | null)?.focus()
            }}
            onCloseAutoFocus={(event) => {
              if (!reviewAfterClose.current) return
              reviewAfterClose.current = false
              event.preventDefault()
              showForm()
            }}
          >
            <SheetTitle className="sr-only">Assistant Mahara</SheetTitle>
            <SheetDescription className="sr-only">
              Répondez aux questions : l'assistant remplit le formulaire pour vous.
            </SheetDescription>
            <AssistantChat chat={chat} onClose={() => setAssistantOpen(false)} onReview={review} />
          </SheetContent>
        </Sheet>
      )}
    </section>
  )
}
