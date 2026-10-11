import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router'
import { ApiError, applyToOffer, getGovernorates, getOffers, refreshMatches, type Governorate, type JobOffer } from '@/lib/api'
import { PageTitle } from './placeholders'

const contractLabels: Record<string, string> = {
  cdi: 'CDI', cdd: 'CDD', sivp: 'SIVP', karama: 'KARAMA', internship: 'Stage',
  freelance: 'Freelance', seasonal: 'Saisonnier', daily_work: 'Journalier',
}

const workModeLabels: Record<string, string> = { on_site: 'Sur site', remote: 'À distance', hybrid: 'Hybride' }

function errorMessage(error: unknown): string {
  if (error instanceof ApiError && typeof error.detail === 'string') return error.detail
  return 'Une erreur est survenue. Réessayez.'
}

export function OffresPage() {
  const [offers, setOffers] = useState<JobOffer[]>([])
  const [governorates, setGovernorates] = useState<Governorate[]>([])
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState<string | null>(null)
  const [notice, setNotice] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [offerItems, governorateItems] = await Promise.all([getOffers(), getGovernorates()])
      setOffers(offerItems)
      setGovernorates(governorateItems)
      setNotice('')
    } catch (error) {
      setNotice(errorMessage(error))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { void load() }, [load])

  async function apply(offer: JobOffer) {
    setBusy(offer.offer_id)
    setNotice('')
    try {
      await refreshMatches()
      await applyToOffer(offer.offer_id)
      setNotice('Votre candidature a été envoyée.')
      await load()
    } catch (error) {
      setNotice(errorMessage(error))
    } finally {
      setBusy(null)
    }
  }

  const governorateName = (code: string) => governorates.find((item) => item.code === code)?.name_fr ?? code

  return (
    <section className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div><PageTitle>Offres d'emploi</PageTitle><p className="mt-2 text-sm text-ink-secondary">Les offres publiées près de chez vous.</p></div>
        <button className="min-h-11 rounded-[10px] bg-teal px-4 text-sm font-semibold text-white" type="button" onClick={() => void load()} disabled={loading}>Actualiser</button>
      </div>
      {notice && <p className="rounded-[10px] border border-line bg-surface p-4 text-sm text-ink-secondary" role="status">{notice}</p>}
      {loading ? <p className="rounded-[10px] border border-line bg-surface p-5 text-ink-secondary">Chargement des offres…</p> : null}
      {!loading && offers.length === 0 && <p className="rounded-[10px] border border-line bg-surface p-5 text-ink-secondary">Aucune offre publiée pour le moment.</p>}
      <div className="grid gap-4 xl:grid-cols-2">
        {offers.map((offer) => (
          <article key={offer.offer_id} className="space-y-4 rounded-[10px] border border-line bg-surface p-5">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div><h2 className="text-lg font-semibold text-ink">{offer.title}</h2><p className="mt-1 text-sm text-ink-secondary">{governorateName(offer.governorate_code)}{offer.delegation ? ` · ${offer.delegation}` : ''} · {contractLabels[offer.contract_type] ?? offer.contract_type}</p></div>
              {offer.match_score !== null && <span className="rounded-full bg-secondary px-3 py-1 text-sm font-semibold text-teal">{Math.round(offer.match_score)} % compatible</span>}
            </div>
            <p className="whitespace-pre-line text-sm leading-6 text-ink-secondary">{offer.description}</p>
            <div className="flex flex-wrap gap-x-4 gap-y-2 text-xs text-ink-secondary">
              <span>{workModeLabels[offer.work_mode] ?? offer.work_mode}</span>
              <span>{offer.positions_count} poste{offer.positions_count > 1 ? 's' : ''}</span>
              <span>{offer.min_years_experience} an(s) d'expérience minimum</span>
              {(offer.salary_min_tnd !== null || offer.salary_max_tnd !== null) && <span>{offer.salary_min_tnd ?? '—'}–{offer.salary_max_tnd ?? '—'} TND</span>}
            </div>
            <div className="flex flex-wrap gap-2">{offer.skills.slice(0, 6).map((skill) => <span key={skill.code} className="rounded-full bg-page px-3 py-1 text-xs text-ink-secondary">{skill.label_fr}</span>)}</div>
            <div className="flex flex-wrap items-center justify-between gap-3 border-t border-line pt-4">
              <Link to="/candidatures" className="text-sm font-medium text-teal underline">Mes candidatures</Link>
              <button type="button" className="min-h-11 rounded-[10px] bg-gold px-4 font-semibold text-gold-foreground" disabled={busy !== null || offer.application_status !== null} onClick={() => void apply(offer)}>{busy === offer.offer_id ? 'Envoi…' : offer.application_status ? 'Candidature envoyée' : 'Postuler'}</button>
            </div>
          </article>
        ))}
      </div>
    </section>
  )
}
