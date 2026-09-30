import { ArrowLeft, Clock } from 'lucide-react'
import type { ReactNode } from 'react'
import { Link } from 'react-router'

import { Button } from '@/components/ui/button'

export function PageTitle({ children }: { children: ReactNode }) {
  return <h1 className="text-2xl text-ink lg:text-3xl">{children}</h1>
}

function ComingSoon({ title, backTo }: { title: string; backTo?: { to: string; label: string } }) {
  return (
    <section className="space-y-4">
      <PageTitle>{title}</PageTitle>
      <div className="flex items-center gap-3 rounded-[10px] border bg-surface p-5 text-ink-secondary">
        <Clock aria-hidden className="size-5 shrink-0 text-teal" />
        <p>Bientôt disponible</p>
      </div>
      {backTo && (
        <Button asChild variant="outline">
          <Link to={backTo.to}>
            <ArrowLeft aria-hidden />
            {backTo.label}
          </Link>
        </Button>
      )}
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

export function ProfilFormPage() {
  return <ComingSoon title="Mon profil" backTo={{ to: '/profil', label: 'Retour au profil' }} />
}

export function CvImportPage() {
  return <ComingSoon title="Importer mon CV" backTo={{ to: '/profil', label: 'Retour au profil' }} />
}
