import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import {
  createMyRoadmap,
  getCareerOptions,
  getMyRoadmaps,
  updateRoadmapStatus,
  updateRoadmapStep,
  type CareerOption,
  type MatchRoadmap,
  type Roadmap,
} from '../lib/api'

function replaceRoadmap(roadmaps: Roadmap[], updated: Roadmap) {
  return roadmaps.map((roadmap) => roadmap.roadmap_id === updated.roadmap_id ? updated : roadmap)
}

function marketLabel(option: CareerOption) {
  const signal = option.market_signal
  const latest = signal.latest_offer_at
    ? ` Latest observed posting: ${new Date(signal.latest_offer_at).toLocaleDateString()}.`
    : ''
  if (signal.status === 'increasing') {
    return `Observed job postings increased ${signal.change_percent}% (${signal.previous_positions} to ${signal.current_positions} positions in consecutive 90-day periods).${latest}`
  }
  if (signal.status === 'stable_or_declining') {
    return `Observed job postings: ${signal.previous_positions} to ${signal.current_positions} positions in consecutive 90-day periods.${latest}`
  }
  return `Not enough recent posting data to assess a trend (minimum ${signal.minimum_positions_per_period} positions per period).${latest}`
}

export function RoadmapsPage() {
  const [roadmaps, setRoadmaps] = useState<Roadmap[]>([])
  const [options, setOptions] = useState<CareerOption[]>([])
  const [marketMethod, setMarketMethod] = useState('')
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState('')
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  async function load() {
    setLoading(true)
    setError('')
    try {
      const [saved, careers] = await Promise.allSettled([getMyRoadmaps(), getCareerOptions()])
      const errors: string[] = []
      if (saved.status === 'fulfilled') setRoadmaps(saved.value)
      else errors.push(saved.reason instanceof Error ? saved.reason.message : 'Could not load saved roadmaps.')
      if (careers.status === 'fulfilled') {
        setOptions(careers.value.items)
        setMarketMethod(careers.value.market_method)
      } else {
        errors.push(careers.reason instanceof Error ? careers.reason.message : 'Could not load career options.')
      }
      if (errors.length) setError(errors.join(' '))
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not load career roadmaps.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void load() }, [])

  async function startRoadmap(option: CareerOption) {
    setBusy(option.occupation_code)
    setError('')
    setNotice('')
    try {
      const result: MatchRoadmap = await createMyRoadmap({ target_occupation_code: option.occupation_code })
      if ('steps' in result) {
        if (result.roadmap_id) {
          setRoadmaps((current) => current.some((item) => item.roadmap_id === result.roadmap_id)
            ? replaceRoadmap(current, result)
            : [result, ...current])
          setNotice(`Your roadmap for ${option.title} is ready.`)
        } else {
          setNotice(`Your roadmap for ${option.title} was generated.`)
        }
      } else {
        setNotice(result.message)
      }
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not create this roadmap.')
    } finally {
      setBusy('')
    }
  }

  async function saveStep(roadmap: Roadmap, position: number, status: Roadmap['steps'][number]['status']) {
    if (!roadmap.roadmap_id) return
    const key = `${roadmap.roadmap_id}-${position}`
    setBusy(key)
    setError('')
    try {
      const updated = await updateRoadmapStep(roadmap.roadmap_id, position, status)
      setRoadmaps((current) => replaceRoadmap(current, updated))
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not update this step.')
    } finally {
      setBusy('')
    }
  }

  async function archiveRoadmap(roadmap: Roadmap) {
    if (!roadmap.roadmap_id) return
    setBusy(roadmap.roadmap_id)
    setError('')
    try {
      const updated = await updateRoadmapStatus(
        roadmap.roadmap_id,
        roadmap.status === 'abandoned' ? 'active' : 'abandoned',
      )
      setRoadmaps((current) => replaceRoadmap(current, updated))
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not update this roadmap.')
    } finally {
      setBusy('')
    }
  }

  return (
    <div className="stacked-view career-roadmaps">
      <header className="panel-header">
        <div>
          <p className="eyebrow">Career development</p>
          <h2>My learning roadmaps</h2>
          <p>Choose a role, see how your existing skills can help, and track the steps you take.</p>
        </div>
        <Link className="secondary-btn" to="/matches">View job matches</Link>
      </header>

      {error && <div className="stacked-inline-error" role="alert">
        <p className="form-error">{error}</p>
        <button className="secondary-btn" type="button" onClick={() => void load()}>Try again</button>
      </div>}
      {notice && <p className="form-notice" role="status">{notice}</p>}

      {loading ? <p role="status">Loading your roadmaps and career options…</p> : <>
        <section className="detail-panel">
          <div className="section-heading">
            <div><p className="eyebrow">Explore transitions</p><h3>Roles that may fit your skills</h3></div>
            <span className="module-tag">{options.length} options</span>
          </div>
          <p className="career-market-method">{marketMethod}</p>
          <p className="career-market-method">Occupation goals use level 2 of 4 as a planning baseline; job-offer roadmaps use the employer's specified skill level.</p>
          {options.length === 0 ? <p>No validated occupations are available yet.</p> : <div className="career-option-grid">
            {options.map((option) => <article className="career-option" key={option.occupation_code}>
              <div className="section-heading">
                <div><h4>{option.title}</h4><small>{option.occupation_code}</small></div>
                <span className="module-tag">{option.gaps.length} skill gaps</span>
              </div>
              {option.description && <p>{option.description}</p>}
              <p>
                Matching skills: {option.matched_skill_labels.join(', ') || 'none identified'}.
                {' '}Potentially transferable: {option.transferable_skills.map((skill) => skill.label).join(', ') || 'none identified'}.
              </p>
              <p className="career-market-signal">{marketLabel(option)}</p>
              {option.gaps.length > 0 && <details>
                <summary>Skills to develop ({option.gaps.length})</summary>
                <ul>{option.gaps.slice(0, 6).map((gap) => <li key={gap.skill_code}>
                  {gap.skill_label}
                  {gap.transferable_skill_codes.length > 0 && <small> Related experience: {gap.transferable_skill_codes.map((code) =>
                    option.transferable_skills.find((skill) => skill.skill_code === code)?.label ?? code
                  ).join(', ')}</small>}
                </li>)}</ul>
              </details>}
              <button
                className="primary-btn"
                type="button"
                disabled={Boolean(busy) || option.gaps.length === 0}
                onClick={() => void startRoadmap(option)}
              >
                {busy === option.occupation_code ? 'Building roadmap…' : option.gaps.length === 0 ? 'You meet current skill requirements' : 'Build this roadmap'}
              </button>
            </article>)}
          </div>}
        </section>

        <section className="detail-panel">
          <div className="section-heading">
            <div><p className="eyebrow">Your plans</p><h3>Saved roadmaps</h3></div>
            <span className="module-tag">{roadmaps.length} roadmaps</span>
          </div>
          {roadmaps.length === 0 ? <p>No roadmaps saved yet. Choose a career goal above or start from one of your job matches.</p> : <div className="saved-roadmaps">
            {roadmaps.map((roadmap) => <article className="saved-roadmap" key={roadmap.roadmap_id}>
              <div className="section-heading">
                <div>
                  <p className="eyebrow">{roadmap.target_job_title ? 'Job offer' : 'Occupation goal'}</p>
                  <h4>{roadmap.target_job_title ?? roadmap.target_occupation_title ?? roadmap.target_occupation_code}</h4>
                </div>
                <span className="module-tag">{roadmap.status.replace('_', ' ')}</span>
              </div>
              <label className="roadmap-progress">
                <span>{roadmap.progress_pct}% complete</span>
                <progress max="100" value={roadmap.progress_pct} aria-label={`${roadmap.progress_pct}% complete`} />
              </label>
              {roadmap.market_signal && <p className="career-market-signal">
                Career market signal: {roadmap.market_signal.status.replace(/_/g, ' ')}. {roadmap.market_signal.source}.
              </p>}
              <ol className="roadmap-steps">
                {roadmap.steps.map((step) => <li key={step.position}>
                  <div className="roadmap-step-title">
                    <strong>{step.skill_label ?? step.skill_code}</strong>
                    <small>{step.current_level === null ? 'Not in your current profile' : `Current level ${step.current_level}`} · target level {step.required_level}</small>
                  </div>
                  {step.transferable_skills.length > 0 && <p>Potentially relevant skills you already have: {step.transferable_skills.map((skill) => skill.label).join(', ')}.</p>}
                  <p>{step.learning_action}</p>
                  {step.courses.length > 0 && <ul className="roadmap-courses">
                    {step.courses.map((course) => <li key={course.course_id}>
                      <strong>{course.title}</strong> · {course.provider_name}
                      <small>
                        Teaches up to level {course.target_level} ·{' '}
                        {course.modality.replace('_', ' ')}
                        {course.duration_hours ? ` · ${course.duration_hours} hours` : ''}
                        {course.cost_tnd === 0 ? ' · Free' : course.cost_tnd !== null ? ` · ${course.cost_tnd} TND` : ''}
                        {course.governorate_code ? ` · ${course.governorate_code}` : ''}
                      </small>
                      <small>Active catalog listing; provider verification is not represented in the current catalog. Confirm availability and details directly.</small>
                    </li>)}
                  </ul>}
                  <label className="roadmap-step-status">
                    Progress
                    <select
                      value={step.status}
                      disabled={Boolean(busy)}
                      onChange={(event) => void saveStep(roadmap, step.position, event.target.value as typeof step.status)}
                    >
                      <option value="todo">Not started</option>
                      <option value="in_progress">In progress</option>
                      <option value="done">Done</option>
                      <option value="skipped">Skip for now</option>
                    </select>
                  </label>
                </li>)}
              </ol>
              <button
                className="ghost-btn"
                type="button"
                disabled={Boolean(busy)}
                onClick={() => void archiveRoadmap(roadmap)}
              >
                {roadmap.status === 'abandoned' ? 'Resume roadmap' : 'Archive roadmap'}
              </button>
            </article>)}
          </div>}
        </section>
      </>}
    </div>
  )
}
