import { ArrowLeft, CircleAlert, FileText, FileUp, Info, Pencil, RefreshCcw } from 'lucide-react'
import { useCallback, useEffect, useRef, useState, type DragEvent } from 'react'
import { Link, useLocation, useNavigate } from 'react-router'

import { ProfileForm } from '@/components/profile/ProfileForm'
import { draftToFormStart } from '@/components/profile/cv-draft'
import type { ProfileFormStart } from '@/components/profile/form-values'
import { Button } from '@/components/ui/button'
import { ApiError, MAX_CV_BYTES, getProfile, importCv, type Profile } from '@/lib/api'
import { useAuth } from '@/lib/auth-context'
import { cn } from '@/lib/utils'
import { PageTitle } from './placeholders'

const ACCEPT = '.pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document'
const WRONG_TYPE = "Ce fichier n'est pas accepté. Choisissez un PDF ou un fichier Word (.docx)."
const TOO_BIG = 'Ce fichier est trop lourd : 5 Mo au maximum.'

type Loaded = { status: 'loading' } | { status: 'error' } | { status: 'ready'; profile: Profile | null }

type Step =
  | { status: 'pick'; error?: string; unreadable?: boolean }
  | { status: 'sending'; fileName: string; sent: number }
  | { status: 'review'; start: ProfileFormStart; found: string; unmatched: string[] }

/**
 * Import a CV (PDF or DOCX): the backend reads it and returns a draft, which opens the profile form
 * prefilled. Nothing is saved until "Enregistrer"; the profile is then marked as coming from a CV.
 */
export function CvImportPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { session } = useAuth()
  // The Profil page hands over the profile it already has (null = none yet); a direct visit loads it,
  // because the CV is added to an existing profile rather than replacing it.
  const handedOver: { profile: Profile | null } | null =
    location.state && 'profile' in location.state ? location.state : null
  const [loaded, setLoaded] = useState<Loaded>(() =>
    handedOver ? { status: 'ready', profile: handedOver.profile } : { status: 'loading' },
  )
  const [step, setStep] = useState<Step>({ status: 'pick' })

  const load = useCallback(() => {
    let ignore = false
    getProfile()
      .then((profile) => {
        if (!ignore) setLoaded({ status: 'ready', profile })
      })
      .catch(() => {
        if (!ignore) setLoaded({ status: 'error' })
      })
    return () => {
      ignore = true
    }
  }, [])

  const [needsLoad] = useState(!handedOver)
  useEffect(() => (needsLoad ? load() : undefined), [load, needsLoad])

  useEffect(() => {
    if (step.status === 'review') window.scrollTo({ top: 0 })
  }, [step.status])

  if (loaded.status !== 'ready') {
    return (
      <section className="space-y-4">
        <PageTitle>Importer mon CV</PageTitle>
        {loaded.status === 'loading' ? (
          <p role="status" className="text-ink-secondary">Chargement…</p>
        ) : (
          <div role="alert" className="space-y-3 rounded-[10px] border bg-surface p-5">
            <p className="text-danger">Impossible de charger votre profil.</p>
            <Button
              variant="outline"
              onClick={() => {
                setLoaded({ status: 'loading' })
                load()
              }}
            >
              Réessayer
            </Button>
          </div>
        )}
      </section>
    )
  }

  const saved = loaded.profile

  async function send(file: File) {
    const name = file.name.toLowerCase()
    if (!name.endsWith('.pdf') && !name.endsWith('.docx')) return setStep({ status: 'pick', error: WRONG_TYPE })
    if (file.size > MAX_CV_BYTES) return setStep({ status: 'pick', error: TOO_BIG })

    setStep({ status: 'sending', fileName: file.name, sent: 0 })
    try {
      const { draft, unmatched_words } = await importCv(file, (sent) =>
        setStep((current) => (current.status === 'sending' ? { ...current, sent } : current)),
      )
      const metadata = session?.user.user_metadata ?? {}
      setStep({
        status: 'review',
        start: draftToFormStart(draft, saved, metadata.full_name || metadata.name || ''),
        found: foundSummary(draft.skills.length, draft.experiences.length, draft.educations.length),
        unmatched: unmatched_words,
      })
    } catch (error) {
      const status = error instanceof ApiError ? error.status : 0
      if (status === 415) setStep({ status: 'pick', error: WRONG_TYPE })
      else if (status === 413) setStep({ status: 'pick', error: TOO_BIG })
      else if (status === 422 && error instanceof ApiError && typeof error.detail === 'string') {
        setStep({ status: 'pick', error: `${error.detail}.`, unreadable: true })
      } else setStep({ status: 'pick', error: "L'envoi a échoué. Vérifiez votre connexion et réessayez." })
    }
  }

  if (step.status === 'review') {
    return (
      <section className="space-y-5">
        <div className="mx-auto max-w-2xl space-y-4">
          <PageTitle>{saved ? 'Compléter mon profil' : 'Créer mon profil'}</PageTitle>
          <div role="status" className="space-y-2 rounded-[10px] border border-gold/60 bg-gold/10 p-4 text-ink">
            <p className="flex items-start gap-2 font-semibold">
              <Info aria-hidden className="mt-0.5 size-5 shrink-0 text-teal" />
              Vérifiez les informations avant d'enregistrer
            </p>
            <p className="text-[15px] text-ink-secondary">
              {step.found}
              {saved && ' Votre profil actuel est gardé ; le CV ajoute seulement ce qui manquait.'}
            </p>
            {step.unmatched.length > 0 && (
              <p className="text-[15px] text-ink-secondary">
                Non reconnu : {step.unmatched.join(', ')}. Cherchez une compétence proche à l'étape 2.
              </p>
            )}
            <Button variant="ghost" className="-ml-3 text-teal" onClick={() => setStep({ status: 'pick' })}>
              <RefreshCcw aria-hidden />
              Choisir un autre fichier
            </Button>
          </div>
        </div>
        <ProfileForm
          initialValues={step.start}
          fromCv
          onSaved={(profile, { photoFailed }) =>
            navigate('/profil', { state: { saved: true, profile, photoFailed } })
          }
        />
      </section>
    )
  }

  return (
    <section className="mx-auto max-w-2xl space-y-5">
      <PageTitle>Importer mon CV</PageTitle>
      <p className="text-ink-secondary">
        Nous lisons votre CV et remplissons le formulaire pour vous. Rien n'est enregistré avant que vous
        appuyiez sur « Enregistrer ».
      </p>

      {step.status === 'sending' ? (
        <Sending fileName={step.fileName} sent={step.sent} />
      ) : (
        <DropZone onFile={send} />
      )}

      {step.status === 'pick' && step.error && (
        <div role="alert" className="space-y-3 rounded-[10px] border border-danger/40 bg-surface p-4">
          <p className="flex items-start gap-2 text-danger">
            <CircleAlert aria-hidden className="mt-0.5 size-5 shrink-0" />
            {step.error}
          </p>
          {step.unreadable && (
            <Button asChild variant="outline" size="lg">
              <Link to="/profil/modifier" state={{ profile: saved }}>
                <Pencil aria-hidden />
                Remplir le formulaire
              </Link>
            </Button>
          )}
        </div>
      )}

      {step.status === 'pick' && (
        <Button asChild variant="outline" size="lg">
          <Link to="/profil">
            <ArrowLeft aria-hidden />
            Retour au profil
          </Link>
        </Button>
      )}
    </section>
  )
}

function foundSummary(skills: number, jobs: number, diplomas: number): string {
  const parts = [
    skills && `${skills} compétence${skills > 1 ? 's' : ''}`,
    jobs && `${jobs} expérience${jobs > 1 ? 's' : ''}`,
    diplomas && `${diplomas} diplôme${diplomas > 1 ? 's' : ''}`,
  ].filter(Boolean)
  return parts.length ? `Trouvé dans votre CV : ${parts.join(', ')}.` : "Nous avons trouvé peu d'informations dans ce CV."
}

/** Drop a file here, or press the button to pick one (camera roll, files...). */
function DropZone({ onFile }: { onFile: (file: File) => void }) {
  const input = useRef<HTMLInputElement>(null)
  const [over, setOver] = useState(false)

  function drop(event: DragEvent) {
    event.preventDefault()
    setOver(false)
    const file = event.dataTransfer.files[0]
    if (file) onFile(file)
  }

  return (
    <div
      onDragOver={(event) => {
        event.preventDefault()
        setOver(true)
      }}
      onDragLeave={() => setOver(false)}
      onDrop={drop}
      className={cn(
        'flex flex-col items-center gap-4 rounded-[10px] border-2 border-dashed bg-surface px-5 py-10 text-center transition-colors',
        over ? 'border-teal bg-secondary' : 'border-line',
      )}
    >
      <div className="flex size-16 items-center justify-center rounded-full bg-secondary text-teal">
        <FileUp aria-hidden className="size-8" />
      </div>
      <div className="space-y-1">
        <p className="text-lg font-medium text-ink">Déposez votre CV ici</p>
        <p className="text-ink-secondary">PDF ou Word (.docx), 5 Mo au maximum</p>
      </div>
      <Button type="button" variant="gold" size="lg" className="w-full max-w-xs" onClick={() => input.current?.click()}>
        <FileText aria-hidden />
        Choisir mon CV
      </Button>
      <input
        ref={input}
        type="file"
        accept={ACCEPT}
        aria-hidden // the button above opens it; screen readers shouldn't hear the same control twice
        className="sr-only"
        tabIndex={-1}
        onChange={(event) => {
          const file = event.target.files?.[0]
          event.target.value = '' // the same file can be picked again after an error
          if (file) onFile(file)
        }}
      />
    </div>
  )
}

function Sending({ fileName, sent }: { fileName: string; sent: number }) {
  const percent = Math.round(sent * 100)
  const reading = percent >= 100
  return (
    <div className="space-y-4 rounded-[10px] border bg-surface p-5">
      <p className="flex items-center gap-2 font-medium text-ink">
        <FileText aria-hidden className="size-5 shrink-0 text-teal" />
        <span className="truncate">{fileName}</span>
      </p>
      <div
        role="progressbar"
        aria-label="Envoi du CV"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={percent}
        className="h-3 overflow-hidden rounded-full bg-secondary"
      >
        <div
          className={cn('h-full rounded-full bg-teal transition-[width]', reading && 'animate-pulse')}
          style={{ width: `${Math.max(percent, 4)}%` }}
        />
      </div>
      <p role="status" className="text-ink-secondary">
        {reading ? 'Lecture du CV…' : `Envoi… ${percent} %`}
      </p>
    </div>
  )
}
