import { useEffect, useState } from 'react'
import { Link } from 'react-router'
import { ApiError, getApplications, type CandidateApplication } from '@/lib/api'
import { PageTitle } from './placeholders'

const statusLabels: Record<string, string> = {
  submitted: 'Envoyée', viewed: 'Consultée', shortlisted: 'Présélectionnée', interview: 'Entretien',
  offer_made: 'Offre reçue', hired: 'Recrutée', rejected: 'Non retenue', withdrawn: 'Retirée',
}

export function CandidaturesPage() {
  const [items, setItems] = useState<CandidateApplication[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    void getApplications()
      .then(setItems)
      .catch((reason: unknown) => setError(reason instanceof ApiError && typeof reason.detail === 'string' ? reason.detail : 'Impossible de charger vos candidatures.'))
      .finally(() => setLoading(false))
  }, [])

  return (
    <section className="space-y-5">
      <div><PageTitle>Mes candidatures</PageTitle><p className="mt-2 text-sm text-ink-secondary">Suivez les réponses des employeurs.</p></div>
      {error && <p className="rounded-[10px] border border-line bg-surface p-4 text-sm text-ink-secondary" role="alert">{error}</p>}
      {loading && <p className="rounded-[10px] border border-line bg-surface p-5 text-ink-secondary">Chargement…</p>}
      {!loading && !error && items.length === 0 && <p className="rounded-[10px] border border-line bg-surface p-5 text-ink-secondary">Vous n'avez pas encore envoyé de candidature. <Link to="/offres" className="font-semibold text-teal underline">Voir les offres</Link></p>}
      {!loading && items.length > 0 && <div className="space-y-3">{items.map((item) => <article key={item.application_id} className="flex flex-wrap items-center justify-between gap-3 rounded-[10px] border border-line bg-surface p-5"><div><h2 className="font-semibold text-ink">{item.title}</h2><p className="mt-1 text-sm text-ink-secondary">Envoyée le {new Date(item.applied_at).toLocaleDateString('fr-TN')}</p>{item.score_global !== null && <p className="mt-1 text-xs text-ink-secondary">Compatibilité au moment de la candidature : {Math.round(item.score_global)} %</p>}</div><span className="rounded-full bg-secondary px-3 py-2 text-sm font-medium text-teal">{statusLabels[item.status] ?? item.status}</span></article>)}</div>}
    </section>
  )
}
