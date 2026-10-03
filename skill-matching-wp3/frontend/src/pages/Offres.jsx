import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { getMatches } from '../api.js'
import ErrorMessage from '../components/ErrorMessage.jsx'
import GapChip from '../components/GapChip.jsx'
import ScoreBadge from '../components/ScoreBadge.jsx'
import ScoreBar from '../components/ScoreBar.jsx'
import Spinner from '../components/Spinner.jsx'
import { useCandidat } from '../context/CandidatContext.jsx'
import { nomGouvernorat } from '../governorates.js'
import { titreOffre } from '../offerLabels.js'

function Offres() {
  const { candidatId, offres, skillLabels, referenceLoading, referenceError } = useCandidat()
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const navigate = useNavigate()

  useEffect(() => {
    let active = true
    setLoading(true)
    getMatches(candidatId)
      .then((matches) => {
        if (!active) return
        setItems(matches.items || [])
        setError('')
      })
      .catch((requestError) => { if (active) setError(requestError.message) })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [candidatId])

  const classifies = [...items].sort((a, b) => b.score_global - a.score_global)

  return (
    <div className="page">
      <header className="page-heading"><div><p className="eyebrow">UN MATCH QUI VOUS RESSEMBLE</p><h1>Offres recommandées</h1><p className="page-intro">Les opportunités classées selon vos compétences et votre profil.</p></div><span className="heading-mark">02 <i>/ 04</i></span></header>
      {(loading || referenceLoading) && <Spinner label="Calcul de vos correspondances…" />}
      {(error || referenceError) && <ErrorMessage message={error || referenceError} onReturn={() => navigate('/profil')} />}
      {!loading && !referenceLoading && !error && !referenceError && classifies.length === 0 && <div className="panel empty-state"><span className="empty-icon">—</span><h2>Aucune offre à afficher</h2><p>Le moteur n’a retourné aucune correspondance pour ce profil.</p></div>}
      {!loading && !referenceLoading && !error && !referenceError && classifies.length > 0 && <div className="results-heading"><span>{classifies.length} offres analysées</span><span>Triées du score le plus élevé au plus faible</span></div>}
      {!loading && !referenceLoading && !error && !referenceError && <div className="offer-list">{classifies.map((match, index) => {
        const offre = offres.find((item) => item.job_offer_id === match.job_offer_id)
        const gaps = match.gaps || []
        return <article className="panel offer-card" key={match.job_offer_id}>
          <div className="offer-rank">{String(index + 1).padStart(2, '0')}<small>RANG</small></div>
          <div className="offer-main"><div className="offer-title-row"><div><span className="step-label">OFFRE {index + 1}</span><h2>{titreOffre(offre, index + 1)}</h2></div><ScoreBadge score={match.score_global} /></div>
            <div className="offer-meta"><span>{nomGouvernorat(offre?.location?.governorate_code)}</span><span>{offre?.min_years_experience ?? 0} ans d’expérience minimum</span><span>{offre?.skills?.length ?? 0} compétences demandées</span></div>
            <ScoreBar value={match.score_global} label="Compatibilité globale" />
            <div className="gap-list">{gaps.length ? gaps.map((gap, gapIndex) => <GapChip key={`${gap.skill_code || gap.label_raw}-${gapIndex}`} gap={gap} skillLabels={skillLabels} />) : <GapChip />}</div>
          </div>
          <Link className="button button-secondary detail-button" to={`/offres/${encodeURIComponent(match.job_offer_id)}`}>Voir le détail <span aria-hidden="true">→</span></Link>
        </article>
      })}</div>}
    </div>
  )
}

export default Offres