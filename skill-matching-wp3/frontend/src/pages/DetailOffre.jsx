import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { getMatches, getOffres } from '../api.js'
import ErrorMessage from '../components/ErrorMessage.jsx'
import ScoreBadge from '../components/ScoreBadge.jsx'
import ScoreBar from '../components/ScoreBar.jsx'
import Spinner from '../components/Spinner.jsx'
import { useCandidat } from '../context/CandidatContext.jsx'
import { nomGouvernorat } from '../governorates.js'

const criteres = [
  ['hard_skills', 'Compétences techniques'],
  ['experience', 'Expérience'],
  ['soft_skills', 'Compétences relationnelles'],
  ['location', 'Localisation'],
]

function cle(skill) {
  return skill.skill_code || (skill.label_raw || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').trim().toLowerCase()
}

function DetailOffre() {
  const { offreId } = useParams()
  const { candidatId, profil } = useCandidat()
  const [match, setMatch] = useState(null)
  const [offre, setOffre] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const navigate = useNavigate()

  useEffect(() => {
    let active = true
    Promise.all([getMatches(candidatId), getOffres()])
      .then(([matches, offres]) => {
        if (!active) return
        setMatch(matches.items?.find((item) => item.job_offer_id === offreId) || null)
        setOffre(offres.find((item) => item.job_offer_id === offreId) || null)
      })
      .catch((requestError) => { if (active) setError(requestError.message) })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [candidatId, offreId])

  const niveaux = new Map((profil?.skills || []).map((skill) => [cle(skill), skill.level]))
  const breakdown = match?.breakdown || {}
  const weights = match?.weights || {}
  const formule = criteres.map(([key]) => `${Number(breakdown[key] || 0).toFixed(1)} × ${(Number(weights[key] || 0) * 100).toFixed(0)} %`).join(' + ')

  return <div className="page">
    <div className="breadcrumb"><Link to="/offres">Offres recommandées</Link><span>/</span><span>{offreId}</span></div>
    {loading && <Spinner label="Chargement du détail…" />}
    {error && <ErrorMessage message={error} onReturn={() => navigate('/profil')} />}
    {!loading && !error && (!match || !offre) && <div className="panel empty-state"><h2>Offre introuvable</h2><p>Cette offre n’est plus disponible dans les données du moteur.</p><Link className="button button-secondary" to="/offres">Retour aux offres</Link></div>}
    {!loading && !error && match && offre && <>
      <header className="page-heading"><div><p className="eyebrow">DÉTAIL DE L’OPPORTUNITÉ</p><h1>{offre.job_offer_id}</h1><p className="page-intro">{nomGouvernorat(offre.location?.governorate_code)} · {offre.min_years_experience} ans d’expérience minimum</p></div><ScoreBadge score={match.score_global} /></header>
      <section className="detail-layout">
        <div className="panel criteria-panel"><div className="panel-heading"><div><span className="step-label">VOTRE MATCH</span><h2>Score par critère</h2></div></div>
          <div className="criteria-list">{criteres.map(([key, label]) => <ScoreBar key={key} value={breakdown[key]} label={label} detail={`Poids dans le calcul : ${(Number(weights[key] || 0) * 100).toFixed(0)} %`} />)}</div>
          <div className="formula-box"><small>FORMULE DU SCORE GLOBAL</small><strong>{formule} = {Number(match.score_global).toFixed(1)}</strong></div>
        </div>
        <div className="panel offer-requirements"><div className="panel-heading"><div><span className="step-label">COMPÉTENCES</span><h2>Ce que l’offre demande</h2></div><span className="count-label">{offre.skills.length} au total</span></div>
          <div className="table-wrap"><table><thead><tr><th>Compétence</th><th>Exigence</th><th>Niveau requis</th><th>Votre niveau</th><th>Statut</th></tr></thead><tbody>{offre.skills.map((skill, index) => {
            const level = niveaux.get(cle(skill))
            const status = level == null ? 'Manquante' : level >= skill.min_level ? 'Acquise' : 'Niveau insuffisant'
            const tone = status === 'Acquise' ? 'good' : status === 'Manquante' ? 'low' : 'medium'
            return <tr key={`${cle(skill)}-${index}`}><td>{skill.label_raw || skill.skill_code}</td><td>{skill.requirement === 'required' ? 'Obligatoire' : 'Facultatif'}</td><td>{skill.min_level}</td><td>{level ?? '—'}</td><td><span className={`status-pill ${tone}`}>{status}</span></td></tr>
          })}</tbody></table></div>
          <div className="requirements-footer"><span>Les niveaux du CV sont estimés automatiquement.</span><Link className="button button-primary" to={`/roadmap/${encodeURIComponent(offreId)}`}>Voir ma roadmap <span aria-hidden="true">→</span></Link></div>
        </div>
      </section>
    </>}
  </div>
}

export default DetailOffre