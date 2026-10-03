import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { getRoadmap } from '../api.js'
import ErrorMessage from '../components/ErrorMessage.jsx'
import ScoreBar from '../components/ScoreBar.jsx'
import Spinner from '../components/Spinner.jsx'
import { useCandidat } from '../context/CandidatContext.jsx'
import { libelleCompetence, titreOffre } from '../offerLabels.js'

function Roadmap() {
  const { offreId } = useParams()
  const { candidatId, offres, skillLabels, referenceLoading, referenceError } = useCandidat()
  const [roadmap, setRoadmap] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const navigate = useNavigate()

  useEffect(() => {
    let active = true
    getRoadmap(candidatId, offreId)
      .then((result) => { if (active) setRoadmap(result) })
      .catch((requestError) => { if (active) setError(requestError.message) })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [candidatId, offreId])

  const noGap = roadmap?.status === 'no_gap'
  const steps = roadmap?.steps || []
  const offre = offres.find((item) => item.job_offer_id === offreId) || null
  const numeroOffre = offres.findIndex((item) => item.job_offer_id === offreId) + 1
  const titre = titreOffre(offre, numeroOffre || 1)

  return <div className="page">
    <div className="breadcrumb"><Link to={`/offres/${encodeURIComponent(offreId)}`}>{titre}</Link><span>/</span><span>Ma roadmap</span></div>
    <header className="page-heading"><div><p className="eyebrow">VOTRE PROCHAINE ÉTAPE</p><h1>Ma roadmap</h1><p className="page-intro">Un parcours de compétences associé à <strong>{titre}</strong>.</p></div><span className="heading-mark">04 <i>/ 04</i></span></header>
    {(loading || referenceLoading) && <Spinner label="Préparation de votre roadmap…" />}
    {(error || referenceError) && <ErrorMessage message={error || referenceError} onReturn={() => navigate('/profil')} />}
    {!loading && !referenceLoading && !error && !referenceError && noGap && <section className="panel congratulations"><span className="congrats-symbol">✓</span><p className="eyebrow">OBJECTIF ATTEINT</p><h2>Votre profil couvre toutes les compétences de l’offre.</h2><p>{roadmap.message || 'Aucune compétence à ajouter à votre parcours.'}</p><Link className="button button-primary" to={`/offres/${encodeURIComponent(offreId)}`}>Revoir le détail de l’offre <span aria-hidden="true">→</span></Link></section>}
    {!loading && !referenceLoading && !error && !referenceError && !noGap && <section className="panel roadmap-panel">
      {steps.length === 0 ? <div className="empty-state"><h2>Aucune étape disponible</h2><p>Le moteur n’a retourné aucune étape pour cette offre.</p></div> : <>
        <div className="panel-heading"><div><span className="step-label">PARCOURS PERSONNALISÉ</span><h2>{steps.length} compétences à développer</h2></div><span className="progress-percent">{roadmap.progress_pct}%</span></div>
        <ScoreBar value={roadmap.progress_pct} label="Progression" />
        <ol className="roadmap-steps">{steps.map((step) => <li key={step.position} className="roadmap-step"><span className="step-number">{String(step.position).padStart(2, '0')}</span><div className="roadmap-skill"><strong>{libelleCompetence(step, skillLabels)}</strong><span>Formation recommandée : bientôt (catalogue WP1)</span></div><span className="todo-label">À travailler</span></li>)}</ol>
      </>}
    </section>}
  </div>
}

export default Roadmap