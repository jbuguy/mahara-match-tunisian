import { useState, type FormEvent } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'

import { API_BASE_URL, requestJson } from '../lib/api'

type Role = 'candidate' | 'employer'

export function SignInPage() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const requestedRole = searchParams.get('role')
  const role: Role | null = requestedRole === 'candidate' || requestedRole === 'employer' ? requestedRole : null
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!role) return
    setError('')
    setIsSubmitting(true)
    try {
      const token = await requestJson<{ access_token: string }>(role === 'candidate' ? '/candidates/login' : '/employers/login', {
        method: 'POST', body: JSON.stringify({ email, password }),
      })
      localStorage.setItem('mahara_access_token', token.access_token)
      window.dispatchEvent(new Event('mahara-auth-changed'))
      navigate('/dashboard', { replace: true })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to sign in. Check your details and try again.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="auth-card auth-card-polished">
      <div className="auth-intro">
        <p className="eyebrow">Welcome back</p>
        <h2>{role ? `Sign in to your ${role} workspace` : 'Sign in to your workspace'}</h2>
        <p>{role ? 'Continue where you left off.' : 'Choose the workspace you want to open.'}</p>
      </div>
      {!role ? <div className="signup-role-grid signin-role-grid">
        <button className="signup-choice" type="button" onClick={() => setSearchParams({ role: 'candidate' })}><h3>I'm looking for work</h3><p>Open your candidate workspace.</p><span>Continue as candidate →</span></button>
        <button className="signup-choice" type="button" onClick={() => setSearchParams({ role: 'employer' })}><h3>I'm hiring</h3><p>Open your employer workspace.</p><span>Continue as employer →</span></button>
      </div> : <>
        <button className="text-button" type="button" onClick={() => { setSearchParams({}); setError('') }}>← Choose another workspace</button>
        {role === 'candidate' && <>
          <div className="auth-method-card signin-google-card">
            <p className="auth-method-title">Sign in with Google</p>
            <p className="auth-method-copy">Continue securely with your Google account.</p>
            <button type="button" className="secondary-btn full-width google-btn" onClick={() => { window.location.href = `${API_BASE_URL}/auth/google` }}><span className="google-g" aria-hidden="true">G</span> Continue with Google</button>
          </div>
          <div className="auth-divider"><span>or use email</span></div>
        </>}
        <form className="auth-form" onSubmit={handleSubmit}>
          <label><span>Email address</span><input autoComplete="email" required type="email" value={email} onChange={(event) => setEmail(event.target.value)} /></label>
          <label><span>Password</span><input autoComplete="current-password" required type="password" value={password} onChange={(event) => setPassword(event.target.value)} /></label>
          {error && <p className="form-error" role="alert">{error}</p>}
          <button type="submit" className="primary-btn full-width" disabled={isSubmitting}>{isSubmitting ? 'Signing in…' : 'Sign in'}</button>
        </form>
      </>}
      <p className="auth-switch">New to Mahara? <Link to={role ? `/signup?role=${role}` : '/signup'}>Create an account</Link></p>
    </div>
  )
}
