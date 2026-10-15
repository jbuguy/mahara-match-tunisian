import { useEffect, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'

import { archiveEmployerOffer, decideApplication, getEmployerApplication, getEmployerApplications, getEmployerOfferEditor, getEmployerOffers, getInterviewInvitations, inviteCandidateToInterview, requestJson, setEmployerOfferStatus, updateEmployerOffer, type EmployerApplication, type EmployerApplicationDetail, type EmployerOffer, type EmployerOfferEditor } from '../lib/api'
import { useVoiceInput } from '../lib/useVoiceInput'
import { ChatPanel, type ChatMessage } from '../components/ChatPanel'

type OfferDraft = {
  [key: string]: unknown
  title: string
  description: string
  status: string
  occupation_code?: string | null
  skills?: { skill_code: string; requirement: string; min_level: number }[]
  location?: { governorate_code?: string; delegation?: string | null }
}
type SalaryBenchmark = { status: 'available' | 'suppressed' | 'unavailable'; occupation_code: string; governorate_code: string | null; region: string | null; currency: 'TND'; period_start: string | null; period_end: string | null; publisher: string | null; sample_size: number | null; minimum_sample_size: number; median_tnd: number | null; p25_tnd: number | null; p75_tnd: number | null; suppression_reason: string | null }
type AgentSession = { id: string; mode?: 'chat' | 'form'; answers?: Record<string, string>; messages: ChatMessage[]; complete: boolean; draft: OfferDraft | null }
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
  const [offerStatusFilter, setOfferStatusFilter] = useState('all')
  const [formAnswers, setFormAnswers] = useState<Record<string, string>>({})
  const [highMatchOnly, setHighMatchOnly] = useState(false)
  const [publishConfirmOpen, setPublishConfirmOpen] = useState(false)
  const [salaryBenchmark, setSalaryBenchmark] = useState<SalaryBenchmark | null>(null)
  const [salaryBenchmarkLoading, setSalaryBenchmarkLoading] = useState(false)
  const [salaryRegion, setSalaryRegion] = useState<'governorate' | 'grand_tunis'>('governorate')
  const [editingOffer, setEditingOffer] = useState<EmployerOfferEditor | null>(null)
  const [editorSkillsJson, setEditorSkillsJson] = useState('[]')
  const [editorLanguagesJson, setEditorLanguagesJson] = useState('[]')
  const [interviewTimes, setInterviewTimes] = useState<Record<string, string>>({})
  const [interviewStatus, setInterviewStatus] = useState<Record<string, string>>({})
  const [reopenExpiry, setReopenExpiry] = useState<Record<string, string>>({})

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
          if (sessions[0]) { setSession(sessions[0]); setFormAnswers(sessions[0].answers ?? {}) }
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

  useEffect(() => {
    const occupationCode = session?.draft?.occupation_code
    const governorateCode = session?.draft?.location?.governorate_code
    if (!occupationCode || typeof occupationCode !== 'string' || !governorateCode || typeof governorateCode !== 'string') {
      setSalaryBenchmark(null)
      setSalaryBenchmarkLoading(false)
      return
    }
    let active = true
    setSalaryBenchmarkLoading(true)
    const params = new URLSearchParams({ occupation_code: occupationCode })
    if (salaryRegion === 'grand_tunis') params.set('region', 'grand_tunis')
    else params.set('governorate_code', governorateCode)
    requestJson<SalaryBenchmark>(`/api/v1/employer/market/salaries?${params.toString()}`)
      .then((result) => { if (active) setSalaryBenchmark(result) })
      .catch(() => { if (active) setSalaryBenchmark(null) })
      .finally(() => { if (active) setSalaryBenchmarkLoading(false) })
    return () => { active = false }
  }, [session?.id, session?.draft?.occupation_code, session?.draft?.location?.governorate_code, salaryRegion])

  async function startOffer(mode: 'chat' | 'form' = 'chat') {
    setPending(true)
    setError('')
    setNotice('')
    try {
      rememberSession(await requestJson<AgentSession>('/employer-agent/sessions', {
        method: 'POST', body: JSON.stringify({ mode }),
      }))
      setFormAnswers({})
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Could not start an offer.')
    } finally {
      setPending(false)
    }
  }

  async function generateOfferFromForm(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!session) return
    setPending(true)
    setError('')
    setNotice('')
    try {
      const updated = await requestJson<AgentSession>(`/employer-agent/sessions/${session.id}/answers`, {
        method: 'POST', body: JSON.stringify({ answers: formAnswers }),
      })
      rememberSession(updated)
      setNotice('The draft is ready. Review every detail before publishing.')
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Could not generate the draft.')
    } finally { setPending(false) }
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
    if (!session) return false
    setPending(true)
    setError('')
    try {
      const updated = await requestJson<AgentSession>(`/employer-agent/sessions/${session.id}/publish`, { method: 'POST' })
      rememberSession(updated)
      setOffers(await getEmployerOffers())
      setNotice('Your job offer is published.')
      return true
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Could not publish this offer.')
      return false
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

  async function openOfferEditor(offerId: string) {
    setPending(true); setError('')
    try {
      const offer = await getEmployerOfferEditor(offerId)
      setEditingOffer(offer); setEditorSkillsJson(JSON.stringify(offer.skills, null, 2)); setEditorLanguagesJson(JSON.stringify(offer.languages_required, null, 2))
    }
    catch (requestError) { setError(requestError instanceof Error ? requestError.message : 'Could not load this offer for editing.') }
    finally { setPending(false) }
  }

  async function saveOfferEdit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!editingOffer) return
    setPending(true); setError('')
    try {
      const updated = { ...editingOffer, skills: JSON.parse(editorSkillsJson), languages_required: JSON.parse(editorLanguagesJson) } as EmployerOfferEditor
      await updateEmployerOffer(updated.offer_id, updated)
      setOffers(await getEmployerOffers()); setEditingOffer(null); setNotice('Offer changes saved and audited.')
    } catch (requestError) { setError(requestError instanceof Error ? requestError.message : 'Could not save offer changes.') }
    finally { setPending(false) }
  }

  async function archiveOffer(offerId: string) {
    if (!window.confirm('Archive this closed offer? It will remain in records and disappear from active offer lists.')) return
    setPending(true); setError('')
    try { await archiveEmployerOffer(offerId); setOffers(await getEmployerOffers()); setNotice('Offer archived. Its applications and history are retained.') }
    catch (requestError) { setError(requestError instanceof Error ? requestError.message : 'Could not archive this offer.') }
    finally { setPending(false) }
  }

  async function changeOfferStatus(offerId: string, status: 'published' | 'closed', expiresAt?: string) {
    setPending(true); setError('')
    try { await setEmployerOfferStatus(offerId, status, expiresAt); setOffers(await getEmployerOffers()); setNotice(`Offer ${status}.`) }
    catch (requestError) { setError(requestError instanceof Error ? requestError.message : 'Could not update offer status.') }
    finally { setPending(false) }
  }

  async function invite(applicationId: string) {
    const localTime = interviewTimes[applicationId]
    if (!localTime) { setError('Choose an interview date and time first.'); return }
    setPending(true); setError('')
    try {
      const result = await inviteCandidateToInterview(applicationId, {
        meeting_at_local: localTime,
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
      })
      setNotice(`Interview invitation ${result.status}. It will show as sent only after mail delivery is confirmed.`)
      setInterviewStatus((current) => ({ ...current, [applicationId]: result.status }))
    } catch (requestError) { setError(requestError instanceof Error ? requestError.message : 'Could not queue the interview invitation.') }
    finally { setPending(false) }
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
    setFormAnswers(updated.answers ?? {})
    setDraftSessions((current) => [updated, ...current.filter((item) => item.id !== updated.id)])
  }

  if (!localStorage.getItem('mahara_access_token')) {
    return <div className="stacked-view"><h2>Employer workspace</h2><p>Sign in with an employer account to create and publish offers.</p><Link className="primary-btn" to="/signin">Sign in</Link></div>
  }
  if (loading) return <div className="stacked-view"><p>Loading employer workspace…</p></div>

  const visibleApplications = applications.filter((application) => (offerFilter === 'all' || application.job_offer_id === offerFilter) && (!highMatchOnly || (application.score_global ?? 0) > 80))
  const visibleOffers = offers.filter((offer) => offerStatusFilter === 'archived' ? Boolean(offer.archived_at) : !offer.archived_at && (offerStatusFilter === 'all' || offer.status === offerStatusFilter))
  const totalApplicants = offers.reduce((sum, offer) => sum + offer.applications_count, 0)

  return (
    <div className="stacked-view">
      <header className="panel-header">
        <div><p className="eyebrow">WP4 · Employer</p><h2>Job offers</h2></div>
        <button className="primary-btn" type="button" onClick={() => void startOffer('chat')} disabled={pending}>New offer</button>
      </header>
      {notice && <p className="form-notice" role="status">{notice}</p>}
      {error && <p className="form-error" role="alert">{error}</p>}
      <section className="employer-intro-banner"><div><strong>National employment network</strong><p>Employer account connected to Mahara Match recruitment services.</p></div><span>Verified workspace</span></section>
      <section className="employer-kpis" aria-label="Recruitment activity"><article><span>Active offers</span><strong>{offers.filter((offer) => offer.status === 'published').length}</strong><small>Published roles</small></article><article><span>Applications</span><strong>{totalApplicants}</strong><small>Across your offers</small></article><article><span>Shortlisted</span><strong>{offers.reduce((sum, offer) => sum + offer.shortlisted_count, 0)}</strong><small>Candidate reviews</small></article><article><span>Hires</span><strong>{offers.reduce((sum, offer) => sum + offer.hired_count, 0)}</strong><small>Successful placements</small></article></section>
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
        <header className="panel-header"><div><h3>Your job offers</h3><p>Published offers can be edited. Closed offers can be archived after pending applications are resolved.</p></div><nav className="employer-offer-filters" aria-label="Filter job offers">{[['all','All'],['published','Published'],['drafts','Drafts'],['archived','Archived']].map(([key,label]) => <button type="button" key={key} className={offerStatusFilter === key ? 'active' : ''} onClick={() => setOfferStatusFilter(key)}>{label} <span>{key === 'all' ? offers.filter((offer) => !offer.archived_at).length + draftSessions.filter((item) => !item.draft || item.draft.status !== 'published').length : key === 'archived' ? offers.filter((offer) => Boolean(offer.archived_at)).length : key === 'drafts' ? draftSessions.filter((item) => !item.draft || item.draft.status !== 'published').length : offers.filter((offer) => !offer.archived_at && offer.status === key).length}</span></button>)}</nav></header>
        {offerStatusFilter === 'drafts' ? !draftSessions.some((item) => !item.draft || item.draft.status !== 'published') ? <p>No saved drafts yet. Start a new offer to create one.</p> : <div className="employer-offer-list">{draftSessions.filter((item) => !item.draft || item.draft.status !== 'published').map((item) => <article className="employer-offer-card" key={item.id}><h4>{item.draft?.title || 'Offer in progress'}</h4><p>{item.draft ? 'Draft ready for review' : 'Guided interview in progress'}</p><button className="secondary-btn" type="button" onClick={() => rememberSession(item)}>Resume draft</button></article>)}</div> : !offers.length ? <p>No published offers yet. Create an offer to start receiving applications.</p> : !visibleOffers.length ? <p>No offers in this status. Select another filter or create an offer.</p> : <div className="employer-offer-list">
          {visibleOffers.map((offer) => <article className="employer-offer-card" key={offer.job_offer_id}>
            <div><h4>{offer.title}</h4><span className={`module-tag status-${offer.status}`}>{offer.status.replaceAll('_', ' ')}</span></div>
            <p>{offer.applications_count} applicants · {offer.shortlisted_count} shortlisted · {offer.hired_count} hired</p>
            <p>Top applicant match: {offer.top_match_score == null ? 'not scored yet' : `${offer.top_match_score}%`}</p>
            <small>{offer.published_at ? `Published ${new Date(offer.published_at).toLocaleDateString()}` : 'Not published'}{offer.expires_at ? ` · Closes ${new Date(offer.expires_at).toLocaleDateString()}` : ''}</small>
            {!offer.archived_at && offer.status === 'published' && <button className="secondary-btn" type="button" onClick={() => void openOfferEditor(offer.job_offer_id)} disabled={pending}>Edit full offer</button>}
            {!offer.archived_at && offer.status === 'published' && <button className="secondary-btn" type="button" onClick={() => void changeOfferStatus(offer.job_offer_id, 'closed')} disabled={pending}>Close applications</button>}
            {!offer.archived_at && offer.status === 'closed' && offer.expires_at && new Date(offer.expires_at) <= new Date() && <label>New expiry to reopen<input type="datetime-local" required value={reopenExpiry[offer.job_offer_id] ?? ''} onChange={(event) => setReopenExpiry((current) => ({ ...current, [offer.job_offer_id]: event.target.value }))} /></label>}
            {!offer.archived_at && offer.status === 'closed' && <button className="secondary-btn" type="button" onClick={() => { const value = reopenExpiry[offer.job_offer_id]; void changeOfferStatus(offer.job_offer_id, 'published', value ? new Date(value).toISOString() : undefined) }} disabled={pending || Boolean(offer.expires_at && new Date(offer.expires_at) <= new Date() && !reopenExpiry[offer.job_offer_id])}>Reopen offer</button>}
            {!offer.archived_at && offer.status === 'closed' && <button className="secondary-btn" type="button" onClick={() => void archiveOffer(offer.job_offer_id)} disabled={pending}>Archive offer</button>}
            {offer.archived_at && <small>Archived {new Date(offer.archived_at).toLocaleDateString()}</small>}
            {editingOffer?.offer_id === offer.job_offer_id && <form className="offer-edit-form" onSubmit={(event) => void saveOfferEdit(event)}><h5>Edit normalized offer</h5>
              <label>Title<input required minLength={3} maxLength={200} value={editingOffer.title} onChange={(event) => setEditingOffer({ ...editingOffer, title: event.target.value })} /></label>
              <label>Description<textarea required minLength={10} value={editingOffer.description} onChange={(event) => setEditingOffer({ ...editingOffer, description: event.target.value })} /></label>
              <div className="offer-edit-grid"><label>Occupation code<input value={editingOffer.occupation_code ?? ''} onChange={(event) => setEditingOffer({ ...editingOffer, occupation_code: event.target.value || null })} /></label><label>Sector code<input value={editingOffer.sector_code ?? ''} onChange={(event) => setEditingOffer({ ...editingOffer, sector_code: event.target.value || null })} /></label>
                <label>Contract type<select value={editingOffer.contract_type} onChange={(event) => setEditingOffer({ ...editingOffer, contract_type: event.target.value })}>{['cdi','cdd','sivp','karama','internship','freelance','seasonal','daily_work'].map((value) => <option key={value}>{value}</option>)}</select></label><label>Work mode<select value={editingOffer.work_mode} onChange={(event) => setEditingOffer({ ...editingOffer, work_mode: event.target.value })}>{['on_site','remote','hybrid'].map((value) => <option key={value}>{value}</option>)}</select></label>
                <label>Governorate code<input required value={editingOffer.location.governorate_code} onChange={(event) => setEditingOffer({ ...editingOffer, location: { ...editingOffer.location, governorate_code: event.target.value } })} /></label><label>Delegation<input value={editingOffer.location.delegation ?? ''} onChange={(event) => setEditingOffer({ ...editingOffer, location: { ...editingOffer.location, delegation: event.target.value || null } })} /></label>
                <label>Positions<input type="number" min={1} max={1000} value={editingOffer.positions_count} onChange={(event) => setEditingOffer({ ...editingOffer, positions_count: Number(event.target.value) })} /></label><label>Minimum experience (years)<input type="number" min={0} max={40} step="0.5" value={editingOffer.min_years_experience} onChange={(event) => setEditingOffer({ ...editingOffer, min_years_experience: Number(event.target.value) })} /></label>
                <label>Minimum salary (TND)<input type="number" min={0} value={editingOffer.salary?.min_tnd ?? ''} onChange={(event) => setEditingOffer({ ...editingOffer, salary: { min_tnd: event.target.value === '' ? null : Number(event.target.value), max_tnd: editingOffer.salary?.max_tnd ?? null, period: editingOffer.salary?.period ?? 'month' } })} /></label><label>Maximum salary (TND)<input type="number" min={0} value={editingOffer.salary?.max_tnd ?? ''} onChange={(event) => setEditingOffer({ ...editingOffer, salary: { min_tnd: editingOffer.salary?.min_tnd ?? null, max_tnd: event.target.value === '' ? null : Number(event.target.value), period: editingOffer.salary?.period ?? 'month' } })} /></label>
                <label>Salary period<select value={editingOffer.salary?.period ?? 'month'} onChange={(event) => setEditingOffer({ ...editingOffer, salary: { min_tnd: editingOffer.salary?.min_tnd ?? null, max_tnd: editingOffer.salary?.max_tnd ?? null, period: event.target.value as 'hour'|'day'|'month' } })}>{['hour','day','month'].map((value) => <option key={value}>{value}</option>)}</select></label><label>Minimum education<select value={editingOffer.education_level_min ?? ''} onChange={(event) => setEditingOffer({ ...editingOffer, education_level_min: event.target.value || null })}>{['','none','primary','lower_secondary','baccalaureate','vocational_cap','vocational_btp','vocational_bts','licence','master','engineer','doctorate'].map((value) => <option key={value}>{value || 'Not specified'}</option>)}</select></label>
                <label>Expiration<input type="datetime-local" value={editingOffer.expires_at?.slice(0,16) ?? ''} onChange={(event) => setEditingOffer({ ...editingOffer, expires_at: event.target.value ? new Date(event.target.value).toISOString() : null })} /></label>
              </div>
              <label>Required and preferred skills (JSON)<textarea rows={6} value={editorSkillsJson} onChange={(event) => setEditorSkillsJson(event.target.value)} /></label><label>Required languages (JSON)<textarea rows={4} value={editorLanguagesJson} onChange={(event) => setEditorLanguagesJson(event.target.value)} /></label>
              <div className="employer-creator-choices"><button className="secondary-btn" type="button" onClick={() => setEditingOffer(null)} disabled={pending}>Cancel</button><button className="primary-btn" type="submit" disabled={pending}>{pending ? 'Saving…' : 'Save offer'}</button></div>
            </form>}
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
        <label className="employer-match-filter"><input type="checkbox" checked={highMatchOnly} onChange={(event) => setHighMatchOnly(event.target.checked)} /> Filter by Mahara match score above 80%</label>
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
              {application.status === 'shortlisted' && <>{application.employer_contact_consent ? <><label>Interview time ({Intl.DateTimeFormat().resolvedOptions().timeZone})<input type="datetime-local" value={interviewTimes[application.application_id] ?? ''} onChange={(event) => setInterviewTimes((current) => ({ ...current, [application.application_id]: event.target.value }))} /></label><button className="secondary-btn" type="button" onClick={() => void invite(application.application_id)} disabled={pending || !interviewTimes[application.application_id]}>Invite to interview</button></> : <p>The candidate has not consented to employer contact; invitations are disabled.</p>}{interviewStatus[application.application_id] && <span className="module-tag">Invitation {interviewStatus[application.application_id]}</span>}<button className="ghost-btn" type="button" onClick={async () => { try { const items = await getInterviewInvitations(application.application_id); setInterviewStatus((current) => ({ ...current, [application.application_id]: items[0]?.status ?? 'none' })) } catch (cause) { setError(cause instanceof Error ? cause.message : 'Could not refresh invitation status.') } }}>Refresh invitation status</button></>}
            </div>
            {selectedApplication === application.application_id && <CandidateApplicationCard detail={candidateDetail} />}
          </article>)}
        </div>}
      </section>
      {!session && <section className="detail-panel employer-creator-start"><div><p className="eyebrow">Intelligent offer creator</p><h3>Create a role aligned with the REM</h3><p>Choose a guided conversation or structured form. The server creates a reviewable draft; publication requires your confirmation.</p></div><div className="employer-creator-choices"><button className="secondary-btn" type="button" onClick={() => void startOffer('chat')} disabled={pending}>Conversation (voice or text)</button><button className="secondary-btn" type="button" onClick={() => void startOffer('form')} disabled={pending}>Classic form</button></div></section>}
      {session && <div className="journey-grid">
        {session.mode === 'form' && !session.draft ? <form className="detail-panel employer-form-creator" onSubmit={(event) => void generateOfferFromForm(event)}><p className="eyebrow">Intelligent offer creator · Structured form</p><h3>Describe the position</h3><p>Required details are sent to the offer drafting service. Review the generated text before publishing.</p>{[['title','Job title',true],['responsibilities','Main responsibilities',true],['location','Governorate and delegation',true],['contract_type','Contract type',true],['required_skills','Required skills',true],['preferred_skills','Preferred skills',false],['experience_and_education','Experience and education',false],['languages_required','Required languages',false],['work_mode','Work arrangement',false],['positions_count','Number of positions',false],['salary','Salary range (TND)',false]].map(([name,label,required]) => <label key={String(name)}>{String(label)}<textarea required={Boolean(required)} rows={name === 'responsibilities' || name === 'required_skills' ? 3 : 2} value={formAnswers[String(name)] ?? ''} onChange={(event) => setFormAnswers((current) => ({ ...current, [String(name)]: event.target.value }))} /></label>)}<div className="employer-creator-choices"><button className="secondary-btn" type="button" onClick={() => setSession(null)} disabled={pending}>Cancel</button><button className="primary-btn" type="submit" disabled={pending}>{pending ? 'Generating draft…' : 'Generate offer draft'}</button></div></form> : <ChatPanel
          variant="compact"
          className="offer-conversation"
          eyebrow="Employer · guided setup"
          title="Guided offer interview"
          description="Answer a few questions, then review the generated offer before publishing."
          messages={session.messages}
          value={message}
          onValueChange={setMessage}
          onSubmit={sendMessage}
          pending={pending || voice.transcribing}
          pendingLabel={voice.transcribing ? 'Transcribing…' : 'Sending…'}
          error={voice.error}
          placeholder="Write your answer…"
          inputLabel="Your answer"
          emptyMessage="Start by answering Mahara’s first question."
          submitLabel="Send answer"
          composerDisabled={Boolean(session.draft) || voice.transcribing}
          composerActions={<button className={voice.recording ? 'secondary-btn voice-recording' : 'secondary-btn'} type="button" onClick={voice.recording ? voice.stop : voice.start} disabled={pending || voice.transcribing}>
            {voice.recording ? 'Stop speaking' : 'Parler'}
          </button>}
          statusNote={voice.recording ? <p className="chat-panel-note" role="status">Recording. Stop when you are done; you can edit the transcript before sending.</p> : null}
        />}
        <section className="detail-panel">
          <h3>{session.draft ? 'Offer draft' : 'Your progress'}</h3>
          {session.draft ? <>
            <div className="job-card"><h4>{session.draft.title}</h4><p>{session.draft.location?.governorate_code ?? 'Location to confirm'}{session.draft.location?.delegation ? ` · ${session.draft.location.delegation}` : ''}</p><p>{session.draft.description}</p><span className="module-tag">{session.draft.status}</span>{session.draft.status !== 'published' && <button className="primary-btn publish-btn" type="button" onClick={() => setPublishConfirmOpen(true)} disabled={pending || !offerReview}>{pending ? 'Publishing…' : 'Publish offer'}</button>}</div>
            {session.draft.occupation_code && session.draft.location?.governorate_code && <section className="employer-salary-benchmark" aria-live="polite"><div><p className="eyebrow">Official territorial data</p><h4>Salary benchmark ? {salaryRegion === 'grand_tunis' ? 'Grand Tunis' : session.draft.location.governorate_code}</h4></div>{salaryBenchmarkLoading ? <p role="status">Loading official salary data?</p> : salaryBenchmark?.status === 'available' ? <><strong>{salaryBenchmark.median_tnd?.toLocaleString()} TND median</strong><p>{salaryBenchmark.p25_tnd != null && salaryBenchmark.p75_tnd != null ? `${salaryBenchmark.p25_tnd.toLocaleString()}?${salaryBenchmark.p75_tnd.toLocaleString()} TND interquartile range ? ` : ''}n={salaryBenchmark.sample_size} ? {salaryBenchmark.publisher} ? {salaryBenchmark.period_start} to {salaryBenchmark.period_end}</p></> : <p>{salaryBenchmark?.suppression_reason ?? 'No official benchmark is available for this occupation and area.'}</p>}{salaryRegion === 'grand_tunis' ? <button className="secondary-btn" type="button" onClick={() => setSalaryRegion('governorate')}>View selected governorate</button> : <button className="secondary-btn" type="button" onClick={() => setSalaryRegion('grand_tunis')}>View Grand Tunis aggregate</button>}</section>}
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
      {publishConfirmOpen && <div className="employer-modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setPublishConfirmOpen(false) }}><section className="employer-confirm-modal" role="dialog" aria-modal="true" aria-labelledby="publish-confirm-title"><button className="employer-modal-close" type="button" aria-label="Close" onClick={() => setPublishConfirmOpen(false)}>?</button><p className="eyebrow">Civic publication review</p><h3 id="publish-confirm-title">Confirm this job offer</h3><p>Publishing shares this offer with the Mahara Match employment network. Confirm that the role description and requirements are accurate and fair.</p><div className="employer-modal-actions"><button className="secondary-btn" type="button" onClick={() => setPublishConfirmOpen(false)} disabled={pending}>Review draft</button><button className="primary-btn" type="button" onClick={async () => { if (await publishOffer()) setPublishConfirmOpen(false) }} disabled={pending}>{pending ? 'Publishing?' : 'Publish offer'}</button></div></section></div>}
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
