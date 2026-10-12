import { useEffect, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'

import { decideApplication, getEmployerApplication, getEmployerApplications, getEmployerOffers, requestJson, type EmployerApplication, type EmployerApplicationDetail, type EmployerOffer } from '../lib/api'
import { useVoiceInput } from '../lib/useVoiceInput'

type ChatMessage = { role: 'assistant' | 'user'; content: string }
type OfferDraft = {
  [key: string]: unknown
  title: string
  description: string
  status: string
  skills?: { skill_code: string; requirement: string; min_level: number }[]
  location?: { governorate_code?: string; delegation?: string | null }
}
type AgentSession = { id: string; messages: ChatMessage[]; complete: boolean; draft: OfferDraft | null }
type OfferReview = {
  rag?: {
    status: string
    message?: string
    suggestions: { field: string; suggestion: string; reason: string; citation_codes: string[]; proposed_skill_code?: string | null }[]
    sources: { skill_code: string; label: string; similarity: number }[]
  }
}

export function EmployerPage() {
  const voice = useVoiceInput('/employer-agent/transcribe')
  const [session, setSession] = useState<AgentSession | null>(null)
  const [draftSessions, setDraftSessions] = useState<AgentSession[]>([])
  const [offerReview, setOfferReview] = useState<OfferReview | null>(null)
  const [applications, setApplications] = useState<EmployerApplication[]>([])
  const [offers, setOffers] = useState<EmployerOffer[]>([])
  const [selectedApplication, setSelectedApplication] = useState<string | null>(null)
  const [offerFilter, setOfferFilter] = useState('all')
  const [candidateDetail, setCandidateDetail] = useState<EmployerApplicationDetail | null>(null)
  const [message, setMessage] = useState('')
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [pending, setPending] = useState(false)

  useEffect(() => {
    if (!voice.transcript) return
    setMessage((current) => current ? `${current.trimEnd()} ${voice.transcript}` : voice.transcript)
    voice.clearTranscript()
  }, [voice.transcript])

  useEffect(() => {
    if (!localStorage.getItem('mahara_access_token')) {
      setLoading(false)
      return
    }
    let active = true
    Promise.all([getEmployerApplications(), getEmployerOffers()])
      .then(([items, ownOffers]) => {
        if (active) {
          setApplications(items)
          setOffers(ownOffers)
        }
      })
      .catch((requestError) => { if (active) setError(requestError instanceof Error ? requestError.message : 'Could not load employer data.') })
    requestJson<AgentSession[]>('/employer-agent/sessions')
      .then((sessions) => {
        if (active) {
          setDraftSessions(sessions)
          if (sessions[0]) setSession(sessions[0])
        }
      })
      .catch((requestError) => { if (active) setError(requestError instanceof Error ? requestError.message : 'Could not load your offers.') })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [])

  useEffect(() => {
    if (!session?.draft) {
      setOfferReview(null)
      return
    }
    let active = true
    requestJson<OfferReview>(`/employer-agent/sessions/${session.id}/review`)
      .then((review) => { if (active) setOfferReview(review) })
      .catch(() => { if (active) setOfferReview(null) })
    return () => { active = false }
  }, [session?.id, session?.draft])

  async function startOffer() {
    setPending(true)
    setError('')
    setNotice('')
    try {
      rememberSession(await requestJson<AgentSession>('/employer-agent/sessions', {
        method: 'POST', body: JSON.stringify({ mode: 'chat' }),
      }))
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Could not start an offer.')
    } finally {
      setPending(false)
    }
  }

  async function sendMessage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!session || !message.trim()) return
    setPending(true)
    setError('')
    try {
      const updated = await requestJson<AgentSession>(`/employer-agent/sessions/${session.id}/messages`, {
        method: 'POST', body: JSON.stringify({ message: message.trim() }),
      })
      rememberSession(updated)
      setMessage('')
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Could not send your answer.')
    } finally {
      setPending(false)
    }
  }

  async function publishOffer() {
    if (!session) return
    setPending(true)
    setError('')
    try {
      const updated = await requestJson<AgentSession>(`/employer-agent/sessions/${session.id}/publish`, { method: 'POST' })
      rememberSession(updated)
      setOffers(await getEmployerOffers())
      setNotice('Your job offer is published.')
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Could not publish this offer.')
    } finally {
      setPending(false)
    }
  }

  async function addSuggestedSkill(skillCode: string) {
    if (!session?.draft) return
    const skills = session.draft.skills ?? []
    if (skills.some((skill) => skill.skill_code === skillCode)) return
    setPending(true)
    setError('')
    try {
      const updated = await requestJson<AgentSession>(`/employer-agent/sessions/${session.id}/draft`, {
        method: 'PATCH',
        body: JSON.stringify({
          draft: { ...session.draft, skills: [...skills, { skill_code: skillCode, requirement: 'preferred', min_level: 1 }] },
        }),
      })
      rememberSession(updated)
      setNotice('Skill suggestion added as preferred. Review it before publishing.')
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Could not add this skill.')
    } finally {
      setPending(false)
    }
  }

  async function decide(applicationId: string, decision: 'shortlisted' | 'hired' | 'rejected') {
    setPending(true)
    setError('')
    try {
      const result = await decideApplication(applicationId, decision)
      setApplications((current) => current.map((item) => item.application_id === result.application_id ? { ...item, status: result.status } : item))
      setNotice(`Application ${result.status}.`)
      setOffers(await getEmployerOffers())
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Could not update this application.')
    } finally {
      setPending(false)
    }
  }

  async function showCandidate(applicationId: string) {
    if (selectedApplication === applicationId) {
      setSelectedApplication(null)
      setCandidateDetail(null)
      return
    }
    setSelectedApplication(applicationId)
    setCandidateDetail(null)
    setError('')
    try {
      setCandidateDetail(await getEmployerApplication(applicationId))
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Could not load candidate details.')
      setSelectedApplication(null)
    }
  }

  function rememberSession(updated: AgentSession) {
    setSession(updated)
    setDraftSessions((current) => [updated, ...current.filter((item) => item.id !== updated.id)])
  }

  if (!localStorage.getItem('mahara_access_token')) {
    return <div className="stacked-view"><h2>Employer workspace</h2><p>Sign in with an employer account to create and publish offers.</p><Link className="primary-btn" to="/signin">Sign in</Link></div>
  }
  if (loading) return <div className="stacked-view"><p>Loading employer workspace…</p></div>

  const visibleApplications = applications.filter((application) => offerFilter === 'all' || application.job_offer_id === offerFilter)

  return (
    <div className="stacked-view">
      <header className="panel-header">
        <div><p className="eyebrow">WP4 · Employer</p><h2>Job offers</h2></div>
        <button className="primary-btn" type="button" onClick={startOffer} disabled={pending}>New offer</button>
      </header>
      {notice && <p className="form-notice" role="status">{notice}</p>}
      {error && <p className="form-error" role="alert">{error}</p>}
      {draftSessions.some((item) => !item.draft || item.draft.status !== 'published') && <section className="detail-panel">
        <h3>Your drafts</h3>
        <div className="employer-offer-list">
          {draftSessions.filter((item) => !item.draft || item.draft.status !== 'published').map((item) => <article className="employer-offer-card" key={item.id}>
            <h4>{item.draft?.title || 'Offer in progress'}</h4>
            <p>{item.draft ? 'Draft ready for review' : 'Interview in progress'}</p>
            <button className="secondary-btn" type="button" onClick={() => rememberSession(item)}>{session?.id === item.id ? 'Currently open' : 'Resume draft'}</button>
          </article>)}
        </div>
      </section>}
      <section className="detail-panel employer-offers-panel">
        <h3>Your job offers</h3>
        {!offers.length ? <p>No published offers yet. Create an offer to start receiving applications.</p> : <div className="employer-offer-list">
          {offers.map((offer) => <article className="employer-offer-card" key={offer.job_offer_id}>
            <div><h4>{offer.title}</h4><span className={`module-tag status-${offer.status}`}>{offer.status.replaceAll('_', ' ')}</span></div>
            <p>{offer.applications_count} applicants · {offer.shortlisted_count} shortlisted · {offer.hired_count} hired</p>
            <p>Top applicant match: {offer.top_match_score == null ? 'not scored yet' : `${offer.top_match_score}%`}</p>
            <small>{offer.published_at ? `Published ${new Date(offer.published_at).toLocaleDateString()}` : 'Not published'}{offer.expires_at ? ` · Closes ${new Date(offer.expires_at).toLocaleDateString()}` : ''}</small>
          </article>)}
        </div>}
      </section>
      <section className="detail-panel">
        <header className="panel-header">
          <h3>Applicants and match review</h3>
          <label>Offer <select value={offerFilter} onChange={(event) => { setOfferFilter(event.target.value); setSelectedApplication(null); setCandidateDetail(null) }}>
            <option value="all">All offers</option>
            {offers.map((offer) => <option key={offer.job_offer_id} value={offer.job_offer_id}>{offer.title}</option>)}
          </select></label>
        </header>
        {!visibleApplications.length ? <p>{applications.length ? 'No applicants for this offer yet.' : 'No applications yet.'}</p> : <div className="application-list">
          {visibleApplications.map((application) => <article className="application-item" key={application.application_id}>
            <div><h4>{application.candidate_name || `Candidate ${application.candidate_id.slice(0, 8)}`}</h4><p>{application.title} · match {application.score_global ?? 'n/a'}%</p><small>Applied {new Date(application.applied_at).toLocaleDateString()}</small><br /><span className="module-tag">{application.status.replaceAll('_', ' ')}</span></div>
            <div className="assistant-chat-tools">
              <button className="secondary-btn" type="button" onClick={() => void showCandidate(application.application_id)} disabled={pending}>{selectedApplication === application.application_id ? 'Hide profile' : 'View profile and match'}</button>
              {application.status !== 'hired' && application.status !== 'rejected' && application.status !== 'withdrawn' && <>
                <button className="secondary-btn" type="button" onClick={() => void decide(application.application_id, 'shortlisted')} disabled={pending}>Shortlist</button>
                <button className="secondary-btn" type="button" onClick={() => void decide(application.application_id, 'rejected')} disabled={pending}>Reject</button>
                <button className="primary-btn" type="button" onClick={() => void decide(application.application_id, 'hired')} disabled={pending}>Accept / hire</button>
              </>}
            </div>
            {selectedApplication === application.application_id && <CandidateApplicationCard detail={candidateDetail} />}
          </article>)}
        </div>}
      </section>
      {!session && <section className="detail-panel"><h3>Offer assistant</h3><p>Build a job offer with the guided interview. Review the generated draft before publishing.</p><button className="secondary-btn" type="button" onClick={startOffer} disabled={pending}>{pending ? 'Starting…' : 'Start guided offer'}</button></section>}
      {session && <div className="journey-grid">
        <section className="detail-panel offer-conversation">
          <h3>Guided offer interview</h3>
          <div className="conversation-log" aria-live="polite">{session.messages.map((item, index) => <div className={`conversation-message ${item.role}`} key={`${index}-${item.role}`}><span>{item.role === 'assistant' ? 'Mahara' : 'You'}</span><p>{item.content}</p></div>)}</div>
          {!session.draft && <form className="conversation-form" onSubmit={sendMessage}>
            <textarea aria-label="Your answer" rows={3} value={message} onChange={(event) => setMessage(event.target.value)} placeholder="Write your answer…" required />
            {voice.error && <p className="form-error" role="alert">{voice.error}</p>}
            {voice.recording && <p role="status">Recording. Stop when you are done; the transcript can be edited before sending.</p>}
            <div className="assistant-chat-tools">
              <button className={voice.recording ? 'secondary-btn voice-recording' : 'secondary-btn'} type="button" onClick={voice.recording ? voice.stop : voice.start} disabled={pending || voice.transcribing}>
                {voice.recording ? 'Stop speaking' : voice.transcribing ? 'Transcribing…' : 'Parler'}
              </button>
              <button className="primary-btn" type="submit" disabled={pending || voice.transcribing || !message.trim()}>{pending ? 'Sending…' : 'Send answer'}</button>
            </div>
          </form>}
        </section>
        <section className="detail-panel">
          <h3>{session.draft ? 'Offer draft' : 'Your progress'}</h3>
          {session.draft ? <>
            <div className="job-card"><h4>{session.draft.title}</h4><p>{session.draft.location?.governorate_code ?? 'Location to confirm'}{session.draft.location?.delegation ? ` · ${session.draft.location.delegation}` : ''}</p><p>{session.draft.description}</p><span className="module-tag">{session.draft.status}</span>{session.draft.status !== 'published' && <button className="primary-btn publish-btn" type="button" onClick={publishOffer} disabled={pending || !offerReview}>{pending ? 'Publishing…' : 'Publish offer'}</button>}</div>
            <section className="offer-rag-review" aria-live="polite">
              <h4>AI improvement suggestions</h4>
              {!offerReview ? <p>Preparing suggestions from validated skills…</p> : offerReview.rag?.status === 'unavailable' ? <p>{offerReview.rag.message}</p> : !offerReview.rag?.suggestions.length ? <p>No additional grounded suggestions were found.</p> : offerReview.rag.suggestions.map((item, index) => {
                const cited = item.citation_codes.map((code) => offerReview.rag?.sources.find((source) => source.skill_code === code)).filter(Boolean)
                return <article className="offer-rag-suggestion" key={`${item.field}-${index}`}>
                  <strong>{item.field.replaceAll('_', ' ')}</strong>
                  <p>{item.suggestion}</p><p>{item.reason}</p>
                  <small>Sources: {cited.map((source) => `${source?.label} (${source?.skill_code})`).join(', ')}</small>
                  {item.field === 'skills' && item.proposed_skill_code && session.draft?.status !== 'published' && !session.draft?.skills?.some((skill) => skill.skill_code === item.proposed_skill_code) && <button className="secondary-btn" type="button" onClick={() => void addSuggestedSkill(item.proposed_skill_code!)} disabled={pending}>Add as preferred skill</button>}
                </article>
              })}
              <small>Suggestions are optional. Review them for accuracy before changing or publishing your offer.</small>
            </section>
          </> : <p>{session.complete ? 'The interview is complete; the assistant is preparing the draft.' : 'Answer the assistant’s questions. Your offer is not published until you confirm it.'}</p>}
        </section>
      </div>}
    </div>
  )
}

function CandidateApplicationCard({ detail }: { detail: EmployerApplicationDetail | null }) {
  if (!detail) return <div className="candidate-application-detail"><p>Loading candidate profile…</p></div>
  const { candidate, match } = detail
  return <div className="candidate-application-detail">
    <h4>Candidate profile</h4>
    <p>{candidate.name || 'Candidate'}{candidate.governorate ? ` · ${candidate.governorate}` : ''}</p>
    <p>{candidate.email || 'No email shared'}{candidate.phone ? ` · ${candidate.phone}` : ''}</p>
    {candidate.summary && <p>{candidate.summary}</p>}
    <p>{candidate.years_experience ?? 'Experience not listed'} years experience · {candidate.education_level?.replaceAll('_', ' ') ?? 'Education not listed'}{candidate.available_from ? ` · Available ${candidate.available_from}` : ''}</p>
    {candidate.languages.length > 0 && <p>Languages: {candidate.languages.map((language) => `${language.code} (level ${language.level}/4)`).join(', ')}</p>}
    {detail.cover_note && <div><strong>Application note</strong><p>{detail.cover_note}</p></div>}
    {match && <div className="candidate-match-detail">
      <strong>Match score: {match.score_global}%</strong>
      <p>Skills {match.breakdown.hard_skills}% · Experience {match.breakdown.experience}% · Soft skills {match.breakdown.soft_skills}% · Location {match.breakdown.location}%</p>
      {match.gaps.length > 0 && <p>Skills to discuss: {match.gaps.map((gap) => `${gap.label} (${gap.gap_type.replaceAll('_', ' ')})`).join(', ')}</p>}
    </div>}
    <div><strong>Skills</strong>{candidate.skills.length ? <ul>{candidate.skills.map((skill) => <li key={skill.code}>{skill.label} · level {skill.level}/4</li>)}</ul> : <p>No skills listed.</p>}</div>
    <div><strong>Experience</strong>{candidate.experience.length ? <ul>{candidate.experience.map((item, index) => <li key={`${item.title}-${index}`}><b>{item.title}</b>{item.duration_months ? ` · ${item.duration_months} months` : ''}{item.informal ? ' · informal experience' : ''}{item.description ? <p>{item.description}</p> : null}</li>)}</ul> : <p>No work history listed.</p>}</div>
    {candidate.education.length > 0 && <div><strong>Education</strong><ul>{candidate.education.map((item, index) => <li key={`${item.level}-${index}`}>{item.level.replaceAll('_', ' ')}{item.field_of_study ? ` · ${item.field_of_study}` : ''}{item.graduation_year ? ` · ${item.graduation_year}` : ''}</li>)}</ul></div>}
    {candidate.desired_occupations.length > 0 && <p>Interested roles: {candidate.desired_occupations.map((item) => item.title).join(', ')}</p>}
  </div>
}
