import { useCallback, useEffect, useState, type ReactNode } from 'react'
import { Link, useLocation, useNavigate } from 'react-router'
import {
  Briefcase,
  CircleCheck,
  CalendarDays,
  FileUp,
  GraduationCap,
  Languages,
  Mail,
  MapPin,
  MessageCircle,
  Pencil,
  Phone,
  Sparkles,
  Target,
  UserRound,
  type LucideIcon,
} from 'lucide-react'

import { Button } from '@/components/ui/button'
import { getProfile, type Experience, type Profile } from '@/lib/api'
import { UserAvatar } from '@/components/Avatar'
import {
  EDUCATION_LEVELS,
  LANGUAGE_LEVELS,
  LANGUAGES,
  SKILL_LEVELS,
  formatDate,
  formatMonthYear,
} from '@/lib/labels'
import { PageTitle } from './placeholders'

type State =
  | { status: 'loading' }
  | { status: 'error' }
  | { status: 'empty' }
  | { status: 'ready'; profile: Profile }

export function ProfilPage() {
  const location = useLocation()
  const navigate = useNavigate()
  // Coming back from the form after a save: it hands over the saved profile (no need to load it again)
  // and we show a message once, then forget it (a reload won't show it again).
  const handedOver: Profile | undefined = location.state?.profile
  const [state, setState] = useState<State>(() =>
    handedOver ? { status: 'ready', profile: handedOver } : { status: 'loading' },
  )
  const [saved] = useState(() => Boolean(location.state?.saved))
  const [photoFailed] = useState(() => Boolean(location.state?.photoFailed))

  useEffect(() => {
    if (location.state?.saved) navigate(location.pathname, { replace: true, state: null })
  }, [location, navigate])

  const load = useCallback(() => {
    let ignore = false
    getProfile()
      .then((profile) => {
        if (!ignore) setState(profile ? { status: 'ready', profile } : { status: 'empty' })
      })
      .catch(() => {
        if (!ignore) setState({ status: 'error' })
      })
    return () => {
      ignore = true
    }
  }, [])

  // Load once on arrival, unless the form handed the profile over.
  const [needsLoad] = useState(!handedOver)
  useEffect(() => (needsLoad ? load() : undefined), [load, needsLoad])

  function retry() {
    setState({ status: 'loading' })
    load()
  }

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
          <Button variant="outline" onClick={retry}>Réessayer</Button>
        </div>
      </section>
    )
  }
  if (state.status === 'empty') return <EmptyProfile />
  return <ProfileView profile={state.profile} saved={saved} photoFailed={photoFailed} />
}

function EmptyProfile() {
  return (
    <section className="space-y-4">
      <PageTitle>Mon profil</PageTitle>
      <div className="flex flex-col items-center gap-5 rounded-[10px] border bg-surface px-5 py-10 text-center">
        <div className="flex size-16 items-center justify-center rounded-full bg-secondary text-teal">
          <UserRound aria-hidden className="size-8" />
        </div>
        <div className="space-y-2">
          <h2 className="text-xl text-ink">Votre profil n'est pas encore créé</h2>
          <p className="text-ink-secondary">Créez-le pour recevoir des offres qui vous correspondent.</p>
        </div>
        <div className="flex w-full max-w-sm flex-col gap-3">
          <Button asChild variant="gold" size="lg">
            <Link to="/profil/modifier" state={{ profile: null }}>
              <Pencil aria-hidden />
              Créer mon profil
            </Link>
          </Button>
          <Button asChild variant="outline" size="lg">
            <Link to="/profil/modifier" state={{ profile: null, assistant: true }}>
              <MessageCircle aria-hidden />
              Remplir avec l'assistant
            </Link>
          </Button>
          <Button asChild variant="outline" size="lg">
            <Link to="/profil/importer-cv" state={{ profile: null }}>
              <FileUp aria-hidden />
              Importer mon CV
            </Link>
          </Button>
        </div>
      </div>
    </section>
  )
}

function ProfileView({ profile, saved, photoFailed }: { profile: Profile; saved: boolean; photoFailed: boolean }) {
  const name = profile.full_name ?? profile.email ?? ''
  const languages = profile.languages
  const facts = [
    profile.education_level && EDUCATION_LEVELS[profile.education_level],
    profile.years_experience != null && yearsLabel(profile.years_experience),
    profile.available_from && `Disponible à partir du ${formatDate(profile.available_from)}`,
  ].filter(Boolean) as string[]

  return (
    <section className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <PageTitle>Mon profil</PageTitle>
        <div className="flex flex-wrap gap-3">
          <Button asChild variant="outline">
            <Link to="/profil/importer-cv" state={{ profile }}>
              <FileUp aria-hidden />
              Importer mon CV
            </Link>
          </Button>
          <Button asChild variant="gold">
            <Link to="/profil/modifier" state={{ profile }}>
              <Pencil aria-hidden />
              Modifier
            </Link>
          </Button>
        </div>
      </div>

      {saved && (
        <p role="status" className="flex items-center gap-2 rounded-[10px] bg-secondary px-4 py-3 font-medium text-teal">
          <CircleCheck aria-hidden className="size-5 shrink-0" />
          Profil enregistré.
        </p>
      )}
      {photoFailed && (
        <p role="alert" className="rounded-[10px] border border-danger/40 bg-surface px-4 py-3 text-danger">
          La photo n'a pas pu être enregistrée. Réessayez depuis « Modifier ».
        </p>
      )}

      {/* Identity and contact */}
      <div className="flex flex-col gap-5 rounded-[10px] border bg-surface p-5 sm:flex-row sm:items-start">
        <UserAvatar name={name} className="size-20 text-2xl" />
        <div className="min-w-0 flex-1 space-y-3">
          <div className="space-y-1">
            <h2 className="text-xl text-ink">{name}</h2>
            {facts.length > 0 && <p className="text-ink-secondary">{facts.join(' · ')}</p>}
          </div>
          <ul className="grid gap-2 text-[15px] text-ink sm:grid-cols-2">
            <ContactLine icon={Mail} label="E-mail" value={profile.email} />
            <ContactLine icon={Phone} label="Téléphone" value={profile.phone} />
            <ContactLine icon={MapPin} label="Gouvernorat" value={profile.governorate?.name_fr} />
          </ul>
        </div>
      </div>

      {profile.summary && (
        <Card icon={UserRound} title="À propos">
          <p className="whitespace-pre-line text-ink">{profile.summary}</p>
        </Card>
      )}

      <Card icon={Sparkles} title="Compétences">
        {profile.skills.length ? (
          <ul className="flex flex-wrap gap-2">
            {profile.skills.map((skill) => (
              <Pill key={skill.code} label={skill.label_fr} detail={SKILL_LEVELS[skill.level]} />
            ))}
          </ul>
        ) : (
          <Empty>Aucune compétence ajoutée.</Empty>
        )}
      </Card>

      <Card icon={Briefcase} title="Expériences">
        {profile.experiences.length ? (
          <ul className="divide-y divide-line">
            {profile.experiences.map((experience) => (
              <li key={experience.id} className="space-y-1 py-3 first:pt-0 last:pb-0">
                <p className="font-medium text-ink">{experience.job_title_raw}</p>
                {experience.employer_name && <p className="text-ink">{experience.employer_name}</p>}
                {experiencePeriod(experience) && (
                  <p className="flex items-center gap-1.5 text-[14px] text-ink-secondary">
                    <CalendarDays aria-hidden className="size-4 shrink-0" />
                    {experiencePeriod(experience)}
                  </p>
                )}
                {experience.description && (
                  <p className="whitespace-pre-line text-[14px] text-ink-secondary">{experience.description}</p>
                )}
              </li>
            ))}
          </ul>
        ) : (
          <Empty>Aucune expérience ajoutée.</Empty>
        )}
      </Card>

      <Card icon={GraduationCap} title="Formation">
        {profile.educations.length ? (
          <ul className="divide-y divide-line">
            {profile.educations.map((education) => (
              <li key={education.id} className="space-y-1 py-3 first:pt-0 last:pb-0">
                <p className="font-medium text-ink">
                  {[education.level && EDUCATION_LEVELS[education.level], education.field_of_study]
                    .filter(Boolean)
                    .join(' · ') || 'Formation'}
                </p>
                {(education.institution || education.graduation_year) && (
                  <p className="text-[14px] text-ink-secondary">
                    {[education.institution, education.graduation_year].filter(Boolean).join(' · ')}
                  </p>
                )}
              </li>
            ))}
          </ul>
        ) : (
          <Empty>Aucune formation ajoutée.</Empty>
        )}
      </Card>

      <Card icon={Target} title="Métiers recherchés">
        {profile.desired_occupations.length ? (
          <ul className="flex flex-wrap gap-2">
            {profile.desired_occupations.map((occupation) => (
              <Pill key={occupation.code} label={occupation.title_fr} />
            ))}
          </ul>
        ) : (
          <Empty>Aucun métier choisi.</Empty>
        )}
      </Card>

      <Card icon={Languages} title="Langues">
        {languages.length ? (
          <ul className="flex flex-wrap gap-2">
            {languages.map((language) => (
              <Pill
                key={language.code}
                label={LANGUAGES[language.code] ?? language.code.toUpperCase()}
                detail={LANGUAGE_LEVELS[language.level] ?? language.level}
              />
            ))}
          </ul>
        ) : (
          <Empty>Aucune langue ajoutée.</Empty>
        )}
      </Card>
    </section>
  )
}

function Card({ icon: Icon, title, children }: { icon: LucideIcon; title: string; children: ReactNode }) {
  return (
    <div className="space-y-4 rounded-[10px] border bg-surface p-5">
      <h2 className="flex items-center gap-2 text-lg text-ink">
        <Icon aria-hidden className="size-5 shrink-0 text-teal" />
        {title}
      </h2>
      {children}
    </div>
  )
}

function ContactLine({ icon: Icon, label, value }: { icon: LucideIcon; label: string; value?: string | null }) {
  return (
    <li className="flex min-w-0 items-center gap-2">
      <Icon aria-hidden className="size-4 shrink-0 text-teal" />
      <span className="sr-only">{label} :</span>
      <span className={value ? 'truncate' : 'text-ink-secondary'}>{value || `${label} non renseigné`}</span>
    </li>
  )
}

function Pill({ label, detail }: { label: string; detail?: string }) {
  return (
    <li className="inline-flex min-h-9 items-center gap-2 rounded-full border border-line bg-secondary px-3.5 py-1.5 text-[14px] text-ink">
      <span className="font-medium">{label}</span>
      {detail && <span className="text-teal">· {detail}</span>}
    </li>
  )
}

function Empty({ children }: { children: ReactNode }) {
  return <p className="text-ink-secondary">{children}</p>
}

function yearsLabel(years: number): string {
  if (years === 0) return "Sans expérience"
  return years === 1 ? "1 an d'expérience" : `${years} ans d'expérience`
}

function experiencePeriod(experience: Experience): string {
  const { start_date: start, end_date: end, duration_months: months } = experience
  const range = start ? `${formatMonthYear(start)} – ${end ? formatMonthYear(end) : "aujourd'hui"}` : ''
  const duration = months ? `${months} mois` : ''
  if (range && duration) return `${range} (${duration})`
  return range || duration
}
