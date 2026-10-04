import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { applyToOffer, getMyApplications, getMyMatches, getMyRoadmap, type CandidateApplication, type MatchResult, type MatchRoadmap, type RankedMatches } from '../lib/api'

function formatSkillCode(code: string) {
  return code.startsWith('UNMAPPED:') ? code.slice('UNMAPPED:'.length) : code
}

export function MatchesPage() {
  const [matches, setMatches] = useState<RankedMatches | null>(null)
  const [applications, setApplications] = useState<CandidateApplication[]>([])
  const [applying, setApplying] = useState('')
  const [roadmap, setRoadmap] = useState<{ offerId: string; result: MatchRoadmap } | null>(null)
  const [roadmapLoading, setRoadmapLoading] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(Boolean(localStorage.getItem('mahara_access_token')))

  useEffect(() => {
    if (!localStorage.getItem('mahara_access_token')) {
      setLoading(false)
      return
    }
    let active = true
    getMyMatches()
      .then(async (result) => {
        if (!active) return
        setMatches(result)
        const currentApplications = await getMyApplications()
        if (active) setApplications(currentApplications)
      })
      .catch((cause) => { if (active) setError(cause instanceof Error ? cause.message : 'Could not load job matches.') })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [])

  async function loadRoadmap(match: MatchResult) {
    setRoadmapLoading(match.job_offer_id)
    setError('')
    try {
      const result = await getMyRoadmap(match.job_offer_id)
      setRoadmap({ offerId: match.job_offer_id, result })
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not load this roadmap.')
    } finally {
      setRoadmapLoading('')
    }
  }

  async function apply(match: MatchResult) {
    setApplying(match.job_offer_id)
    setError('')
    try {
      const application = await applyToOffer(match.job_offer_id)
      setApplications((current) => [...current, application])
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not submit this application.')
    } finally {
      setApplying('')
    }
  }

  if (!localStorage.getItem('mahara_access_token')) {
    return <div className="stacked-view"><h2>Job matches</h2><p>Sign in to see roles matched to your candidate profile.</p><Link className="primary-btn" to="/signin">Sign in</Link></div>
  }

  if (loading) return <div className="stacked-view"><p>Finding your best matches…</p></div>

  const profileMissing = error === 'profile not found'

  return (
    <div className="stacked-view">
      <header className="panel-header">
        <div><p className="eyebrow">WP3 · Skill matching</p><h2>Your job matches</h2></div>
        {matches && <span className="module-tag">{matches.items.length} roles</span>}
      </header>

      {profileMissing ? <section className="detail-panel">
        <h3>Complete your profile first</h3>
        <p>Matches are calculated from your saved skills, experience, and location.</p>
        <Link className="primary-btn" to="/candidate">Open candidate profile</Link>
      </section> : error && <p className="form-error" role="alert">{error}</p>}

      {matches && matches.items.length === 0 && <section className="detail-panel"><h3>No offers to match yet</h3><p>New offers will appear here when they are available.</p></section>}

      {matches && matches.items.length > 0 && <section className="detail-panel match-results" aria-label="Ranked job matches">
        {matches.items.map((match, index) => <article className="match-item" key={match.job_offer_id}>
          <div className="match-heading">
            <div><p className="eyebrow">Rank {index + 1}</p><h3>Offer {match.job_offer_id.slice(0, 8)}</h3><small className="match-id">{match.job_offer_id}</small></div>
            <strong className="match-score" aria-label={`${match.score_global} percent match`}>{match.score_global}%</strong>
          </div>
          <div className="match-breakdown" aria-label="Score breakdown">
            {Object.entries(match.breakdown).map(([label, score]) => <div className="match-metric" key={label}>
              <span>{label.replace('_', ' ')}</span><strong>{score}%</strong>
              <progress max="100" value={score} aria-label={`${label.replace('_', ' ')} score`} />
            </div>)}
          </div>
          <div className="match-gaps">
            <h4>Skill gaps <span>{match.gaps.length}</span></h4>
            {match.gaps.length ? <ul>{match.gaps.map((gap, gapIndex) => <li key={`${gap.skill_code}-${gapIndex}`}>
              <span>{formatSkillCode(gap.skill_code)}</span>
              <small>{gap.gap_type === 'missing' ? 'Missing' : `Level ${gap.current_level} of ${gap.required_level}`} · {gap.requirement}</small>
            </li>)}</ul> : <p>No skill gaps for this role.</p>}
          </div>
          <button className="secondary-btn" type="button" onClick={() => void loadRoadmap(match)} disabled={roadmapLoading === match.job_offer_id}>
            {roadmapLoading === match.job_offer_id ? 'Loading roadmap…' : 'View learning roadmap'}
          </button>
          {(() => {
            const application = applications.find((item) => item.job_offer_id === match.job_offer_id)
            return application
              ? <p className="form-notice" role="status">Application {application.status}</p>
              : <button className="primary-btn" type="button" onClick={() => void apply(match)} disabled={applying === match.job_offer_id}>
                {applying === match.job_offer_id ? 'Applying…' : 'Apply to this offer'}
              </button>
          })()}
          {roadmap?.offerId === match.job_offer_id && <div className="roadmap-result" aria-live="polite">
            {'steps' in roadmap.result ? <>
              <h4>Roadmap</h4>
              <ol>{roadmap.result.steps.map((step) => <li key={step.position}>{formatSkillCode(step.skill_code)} <small>{step.status}</small></li>)}</ol>
            </> : <p>{roadmap.result.message}</p>}
          </div>}
        </article>)}
      </section>}
    </div>
  )
}