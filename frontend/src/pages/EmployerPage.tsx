import { useEffect, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'

import { requestJson } from '../lib/api'

type ChatMessage = { role: 'assistant' | 'user'; content: string }
type OfferDraft = { title: string; description: string; status: string; location?: { governorate_code?: string; delegation?: string | null } }
type AgentSession = { id: string; messages: ChatMessage[]; complete: boolean; draft: OfferDraft | null }

export function EmployerPage() {
  const [session, setSession] = useState<AgentSession | null>(null)
  const [message, setMessage] = useState('')
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [pending, setPending] = useState(false)

  useEffect(() => {
    if (!localStorage.getItem('mahara_access_token')) {
      setLoading(false)
      return
    }
    let active = true
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
      {!session && <section className="detail-panel"><h3>Offer assistant</h3><p>Build a job offer with the WP4 guided interview. Review the generated draft before publishing.</p><button className="secondary-btn" type="button" onClick={startOffer} disabled={pending}>{pending ? 'Starting…' : 'Start guided offer'}</button></section>}
      {session && <div className="journey-grid">
        <section className="detail-panel offer-conversation">
          <h3>Guided offer interview</h3>
          <div className="conversation-log" aria-live="polite">{session.messages.map((item, index) => <div className={`conversation-message ${item.role}`} key={`${index}-${item.role}`}><span>{item.role === 'assistant' ? 'Mahara' : 'You'}</span><p>{item.content}</p></div>)}</div>
          {!session.draft && <form className="conversation-form" onSubmit={sendMessage}><textarea aria-label="Your answer" rows={3} value={message} onChange={(event) => setMessage(event.target.value)} placeholder="Write your answer…" required /><button className="primary-btn" type="submit" disabled={pending || !message.trim()}>{pending ? 'Sending…' : 'Send answer'}</button></form>}
        </section>
        <section className="detail-panel">
          <h3>{session.draft ? 'Offer draft' : 'Your progress'}</h3>
          {session.draft ? <div className="job-card"><h4>{session.draft.title}</h4><p>{session.draft.location?.governorate_code ?? 'Location to confirm'}{session.draft.location?.delegation ? ` · ${session.draft.location.delegation}` : ''}</p><p>{session.draft.description}</p><span className="module-tag">{session.draft.status}</span>{session.draft.status !== 'published' && <button className="primary-btn publish-btn" type="button" onClick={publishOffer} disabled={pending}>{pending ? 'Publishing…' : 'Publish offer'}</button>}</div> : <p>{session.complete ? 'The interview is complete; the assistant is preparing the draft.' : 'Answer the assistant’s questions. Your offer is not published until you confirm it.'}</p>}
        </section>
      </div>}
    </div>
  )
}
