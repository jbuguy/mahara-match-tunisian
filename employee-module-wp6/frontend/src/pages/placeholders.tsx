import { Clock } from 'lucide-react'
import type { ReactNode } from 'react'

export function PageTitle({ children }: { children: ReactNode }) {
  return <h1 className="text-2xl text-ink lg:text-3xl">{children}</h1>
}

function ComingSoon({ title }: { title: string }) {
  return (
    <section className="space-y-4">
      <PageTitle>{title}</PageTitle>
      <div className="flex items-center gap-3 rounded-[10px] border bg-surface p-5 text-ink-secondary">
        <Clock aria-hidden className="size-5 shrink-0 text-teal" />
        <p>Bientôt disponible</p>
      </div>
    </section>
  )
}

export function OffresPage() {
  return <ComingSoon title="Offres d'emploi" />
}

export function CandidaturesPage() {
  return <ComingSoon title="Mes candidatures" />
}

export function FormationPage() {
  return <ComingSoon title="Formation" />
}

export function ProfilPage() {
  return (
    <section className="space-y-4">
      <PageTitle>Mon profil</PageTitle>
      <p className="text-ink-secondary">Votre profil apparaîtra ici.</p>
    </section>
  )
}
