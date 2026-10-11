import { useEffect, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'

import { decideApplication, getEmployerApplications, requestJson, type EmployerApplication } from '../lib/api'
import { useVoiceInput } from '../lib/useVoiceInput'
import { ChatPanel, type ChatMessage } from '../components/ChatPanel'

type OfferDraft = { title: string; description: string; status: string; location?: { governorate_code?: string; delegation?: string | null } }
type AgentSession = { id: string; messages: ChatMessage[]; complete: boolean; draft: OfferDraft | null }

export function EmployerPage() {
  const voice = useVoiceInput('/employer-agent/transcribe')
  const [session, setSession] = useState<AgentSession | null>(null)
  const [applications, setApplications] = useState<EmployerApplication[]>([])
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
    getEmployerApplications()
      .then((items) => { if (active) setApplications(items) })
      .catch((requestError) => { if (active) setError(requestError instanceof Error ? requestError.message : 'Could not load applications.') })
    requestJson<AgentSession[]>('/employer-agent/sessions')
      .then((sessions) => { if (active && sessions[0]) setSession(sessions[0]) })
      .catch((requestError) => { if (active) setError(requestError instanceof Error ? requestError.message : 'Could not load your offers.') })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [])

  async function startOffer() {
    setPending(true)
    setError('')
    setNotice('')
    try {
      setSession(await requestJson<AgentSession>('/employer-agent/sessions', {
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
      setSession(updated)
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
      setSession(updated)
      setNotice('Your job offer is published.')
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Could not publish this offer.')
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
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Could not update this application.')
    } finally {
      setPending(false)
    }
  }

  if (!localStorage.getItem('mahara_access_token')) {
    return <div className="stacked-view"><h2>Employer workspace</h2><p>Sign in with an employer account to create and publish offers.</p><Link className="primary-btn" to="/signin">Sign in</Link></div>
  }
  if (loading) return <div className="stacked-view"><p>Loading employer workspace…</p></div>

  return (
    <div className="stacked-view">
      <header className="panel-header">
        <div><p className="eyebrow">WP4 · Employer</p><h2>Job offers</h2></div>
        <button className="primary-btn" type="button" onClick={startOffer} disabled={pending}>New offer</button>
      </header>
      {notice && <p className="form-notice" role="status">{notice}</p>}
      {error && <p className="form-error" role="alert">{error}</p>}
      <section className="detail-panel">
        <h3>Applications</h3>
        {!applications.length ? <p>No applications yet.</p> : <div className="application-list">
          {applications.map((application) => <article className="application-item" key={application.application_id}>
            <div><h4>{application.title}</h4><p>Candidate {application.candidate_id.slice(0, 8)} · match {application.score_global ?? 'n/a'}%</p><span className="module-tag">{application.status}</span></div>
            <div className="assistant-chat-tools">
              <button className="secondary-btn" type="button" onClick={() => void decide(application.application_id, 'shortlisted')} disabled={pending}>Shortlist</button>
              <button className="secondary-btn" type="button" onClick={() => void decide(application.application_id, 'rejected')} disabled={pending}>Reject</button>
              <button className="primary-btn" type="button" onClick={() => void decide(application.application_id, 'hired')} disabled={pending}>Hire</button>
            </div>
          </article>)}
        </div>}
      </section>
      {!session && <section className="detail-panel"><h3>Offer assistant</h3><p>Build a job offer with the guided interview. Review the generated draft before publishing.</p><button className="secondary-btn" type="button" onClick={startOffer} disabled={pending}>{pending ? 'Starting…' : 'Start guided offer'}</button></section>}
      {session && <div className="journey-grid">
        <ChatPanel
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
        />
        <section className="detail-panel">
          <h3>{session.draft ? 'Offer draft' : 'Your progress'}</h3>
          {session.draft ? <div className="job-card"><h4>{session.draft.title}</h4><p>{session.draft.location?.governorate_code ?? 'Location to confirm'}{session.draft.location?.delegation ? ` · ${session.draft.location.delegation}` : ''}</p><p>{session.draft.description}</p><span className="module-tag">{session.draft.status}</span>{session.draft.status !== 'published' && <button className="primary-btn publish-btn" type="button" onClick={publishOffer} disabled={pending}>{pending ? 'Publishing…' : 'Publish offer'}</button>}</div> : <p>{session.complete ? 'The interview is complete; the assistant is preparing the draft.' : 'Answer the assistant’s questions. Your offer is not published until you confirm it.'}</p>}
        </section>
      </div>}
    </div>
  )
}
