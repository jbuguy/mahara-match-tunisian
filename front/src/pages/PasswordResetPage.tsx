import { useState, type FormEvent } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { requestJson } from '../lib/api'
import { useI18n } from '../lib/i18n'

export function PasswordResetPage() {
  const { t } = useI18n()
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token') ?? ''
  const [email, setEmail] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setMessage(''); setError(''); setBusy(true)
    try {
      if (token) {
        await requestJson('/auth/email/password-reset/confirm', { method: 'POST', body: JSON.stringify({ token, new_password: newPassword }) })
        setMessage('Votre mot de passe a été réinitialisé. Vous pouvez maintenant vous connecter.')
      } else {
        const result = await requestJson<{ message: string; delivery_configured: boolean }>('/auth/email/password-reset/request', { method: 'POST', body: JSON.stringify({ email }) })
        setMessage(result.delivery_configured ? 'Si cette adresse correspond à un compte, un lien de réinitialisation vient d’être envoyé.' : 'La réinitialisation par e-mail n’est pas configurée sur cet environnement.')
      }
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Impossible de traiter la demande. Veuillez réessayer.')
    } finally { setBusy(false) }
  }

  return <main className="auth-simple-page">
    <section className="auth-simple-card">
      <p className="eyebrow">Sécurité du compte</p>
      <h1>{token ? t('auth.passwordResetTitle') : t('auth.passwordForgotTitle')}</h1>
      <p>{token ? t('auth.passwordResetDescription') : t('auth.passwordForgotDescription')}</p>
      <form className="auth-form" onSubmit={handleSubmit}>
        {!token && <label><span>{t('auth.email')}</span><input required type="email" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} /></label>}
        {token && <label><span>{t('auth.password')}</span><input required minLength={8} type="password" autoComplete="new-password" value={newPassword} onChange={(event) => setNewPassword(event.target.value)} /></label>}
        {error && <p className="form-error" role="alert">{error}</p>}
        {message && <p className="form-success" role="status">{message}</p>}
        <button className="primary-btn full-width" disabled={busy}>{busy ? t('status.loading') : token ? t('auth.resetPassword') : t('auth.sendResetLink')}</button>
      </form>
      <Link to="/signin">{t('auth.backToSignIn')}</Link>
    </section>
  </main>
}
