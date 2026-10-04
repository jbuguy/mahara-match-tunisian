import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { API_BASE_URL, requestJson } from '../lib/api'

export function SignInPage() {
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    setIsSubmitting(true)

    try {
      const token = await requestJson<{ access_token: string }>('/employers/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      })
      localStorage.setItem('mahara_access_token', token.access_token)
      navigate('/employer')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to sign in with email and password.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="auth-card">
      <div className="auth-intro">
        <p className="eyebrow">Welcome back</p>
        <h2>Sign in to your workspace</h2>
          <p>Employers can use email and password. Candidates can continue with Google.</p>
      </div>

      <form className="auth-form" onSubmit={handleSubmit}>
        <label>
          <span>Email</span>
          <input type="email" value={email} onChange={(event) => setEmail(event.target.value)} />
        </label>
        <label>
          <span>Password</span>
          <input type="password" value={password} onChange={(event) => setPassword(event.target.value)} />
        </label>
        {error ? <p className="form-error">{error}</p> : null}
        <button type="submit" className="primary-btn" disabled={isSubmitting}>
          {isSubmitting ? 'Signing in…' : 'Continue'}
        </button>
      </form>

      <div className="auth-divider">
        <span>or</span>
      </div>

      <button
        type="button"
        className="secondary-btn full-width"
        onClick={() => {
          window.location.href = `${API_BASE_URL}/auth/google`
        }}
      >
        Continue with Google
      </button>
    </div>
  )
}
