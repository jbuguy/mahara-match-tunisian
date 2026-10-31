import { useEffect, useMemo, useState, type FormEvent } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'

import { requestJson } from '../lib/api'

type EmailActionResponse = { message: string; delivery_configured: boolean }

export function VerifyEmailPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token') ?? ''
  const initialEmail = searchParams.get('email') ?? ''
  const [email, setEmail] = useState(initialEmail)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [cooldown, setCooldown] = useState(0)
  const [verified, setVerified] = useState(false)

  useEffect(() => {
    if (!token) return
    let active = true
    setBusy(true)
    requestJson<{ message: string }>('/auth/email/verification/confirm', {
      method: 'POST',
      body: JSON.stringify({ token }),
    })
      .then((result) => {
        if (!active) return
        setVerified(true)
        setMessage(result.message)
      })
      .catch((cause) => {
        if (active) setError(cause instanceof Error ? cause.message : 'This verification link is no longer valid.')
      })
      .finally(() => { if (active) setBusy(false) })
    return () => { active = false }
  }, [token])

  useEffect(() => {
    if (cooldown <= 0) return
    const timer = window.setInterval(() => setCooldown((current) => Math.max(0, current - 1)), 1000)
    return () => window.clearInterval(timer)
  }, [cooldown])

  const title = useMemo(() => {
    if (verified) return 'Adresse e-mail vérifiée'
    if (token) return busy ? 'Vérification de votre adresse' : 'Lien de vérification'
    return 'Vérifiez votre adresse e-mail'
  }, [busy, token, verified])

  async function resend(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!email.trim() || cooldown > 0) return
    setBusy(true); setError(''); setMessage('')
    try {
      const result = await requestJson<EmailActionResponse>('/auth/email/verification/request', {
        method: 'POST',
        body: JSON.stringify({ email: email.trim() }),
      })
      setMessage(result.delivery_configured
        ? 'Un nouveau lien de vérification a été envoyé. Vérifiez aussi vos courriers indésirables.'
        : 'La vérification par e-mail n’est pas configurée sur cet environnement.')
      setCooldown(60)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Impossible de renvoyer le lien. Veuillez réessayer.')
    } finally { setBusy(false) }
  }

  return <main className="auth-simple-page">
    <section className="auth-simple-card">
      <p className="eyebrow">Sécurité du compte</p>
      <h1>{title}</h1>
      {token ? <>
        {busy && <p role="status">Nous vérifions votre lien…</p>}
        {message && <p className="form-success" role="status">{message}</p>}
        {error && <p className="form-error" role="alert">{error}</p>}
        {(verified || error) && <Link className="primary-btn full-width" to={verified ? '/dashboard' : '/signin'}>{verified ? 'Continuer' : 'Retour à la connexion'}</Link>}
      </> : <>
        <p>Nous avons besoin de confirmer votre adresse avant de vous envoyer les informations importantes de votre compte.</p>
        <form className="auth-form" onSubmit={resend}>
          <label><span>Adresse e-mail</span><input required type="email" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} /></label>
          {error && <p className="form-error" role="alert">{error}</p>}
          {message && <p className="form-success" role="status">{message}</p>}
          <button className="primary-btn full-width" type="submit" disabled={busy || cooldown > 0}>{busy ? 'Envoi…' : cooldown > 0 ? `Renvoyer dans ${cooldown}s` : 'Renvoyer le lien gratuitement'}</button>
        </form>
        <p className="auth-help">Le lien est valable 24 heures. Vous pouvez demander un nouveau lien gratuitement toutes les 60 secondes.</p>
      </>}
      <Link to="/signin">Retour à la connexion</Link>
    </section>
  </main>
}
