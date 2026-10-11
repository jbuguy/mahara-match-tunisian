import { useState, type FormEvent } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'

import { API_BASE_URL, requestJson } from '../lib/api'

type Role = 'candidate' | 'employer'

export function SignUpPage() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const selectedRole = searchParams.get('role') as Role | null
  const role = selectedRole === 'candidate' || selectedRole === 'employer' ? selectedRole : null
  const [fullName, setFullName] = useState('')
  const [companyName, setCompanyName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [sector, setSector] = useState('')
  const [companySize, setCompanySize] = useState('1-10')
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!role) return
    setError('')
    setIsSubmitting(true)
    try {
      if (role === 'candidate') {
        await requestJson('/candidates/signup', {
          method: 'POST',
          body: JSON.stringify({ full_name: fullName.trim(), email, password, onboarding_path: 'cv_upload' }),
        })
      } else {
        await requestJson('/employers/signup', {
          method: 'POST',
          body: JSON.stringify({ company_name: companyName.trim(), email, password, sector: sector.trim(), company_size: companySize }),
        })
      }
      const token = await requestJson<{ access_token: string }>(role === 'candidate' ? '/candidates/login' : '/employers/login', {
        method: 'POST', body: JSON.stringify({ email, password }),
      })
      localStorage.setItem('mahara_access_token', token.access_token)
      window.dispatchEvent(new Event('mahara-auth-changed'))
      navigate(role === 'candidate' ? '/candidate/start' : '/dashboard', { replace: true })
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Unable to create your account. Please try again.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="auth-card auth-card-polished">
      <div className="auth-intro">
        <p className="eyebrow">Create your account</p>
        <h2>{role === 'candidate' ? 'Find work that fits you' : role === 'employer' ? 'Build your hiring workspace' : 'Choose your Mahara workspace'}</h2>
        <p>{role ? 'Create your account to get started. You can update your details later.' : 'Start with a workspace tailored to what you need.'}</p>
      </div>

      {!role && <div className="signup-role-grid">
        <button className="signup-choice" type="button" onClick={() => setSearchParams({ role: 'candidate' })}>
          <span className="auth-choice-icon" aria-hidden="true">↗</span><h3>I'm looking for work</h3>
          <p>Build a profile, explore suitable jobs, and plan your next steps.</p><span>Candidate workspace →</span>
        </button>
        <button className="signup-choice" type="button" onClick={() => setSearchParams({ role: 'employer' })}>
          <span className="auth-choice-icon" aria-hidden="true">＋</span><h3>I'm hiring</h3>
          <p>Publish clear job offers and find people with the right skills.</p><span>Employer workspace →</span>
        </button>
      </div>}

      {role && <>
        <button className="text-button" type="button" onClick={() => { setSearchParams({}); setError('') }}>← Choose another workspace</button>
        {role === 'candidate' && <div className="auth-method-card signup-role-form">
          <p className="auth-method-title">Continue with Google</p>
          <p className="auth-method-copy">Use your Google account to get started quickly.</p>
          <button className="secondary-btn full-width google-btn" type="button" onClick={() => { window.location.href = `${API_BASE_URL}/auth/google` }}>
            <span className="google-g" aria-hidden="true">G</span> Continue with Google
          </button>
        </div>}
        <div className="auth-divider"><span>or sign up with email</span></div>
        <form className="auth-form signup-role-form" onSubmit={handleSubmit}>
          {role === 'candidate' ? <label><span>Full name</span><input autoComplete="name" required maxLength={160} value={fullName} onChange={(event) => setFullName(event.target.value)} /></label> : <>
            <label><span>Company name</span><input autoComplete="organization" required maxLength={160} value={companyName} onChange={(event) => setCompanyName(event.target.value)} /></label>
            <label><span>Sector</span><input required maxLength={120} value={sector} onChange={(event) => setSector(event.target.value)} /></label>
            <label><span>Company size</span><select value={companySize} onChange={(event) => setCompanySize(event.target.value)}><option value="1-10">1–10</option><option value="11-50">11–50</option><option value="51-200">51–200</option><option value="200+">200+</option></select></label>
          </>}
          <label><span>Email address</span><input autoComplete="email" required type="email" value={email} onChange={(event) => setEmail(event.target.value)} /></label>
          <label><span>Password</span><input autoComplete="new-password" required type="password" minLength={8} maxLength={128} value={password} onChange={(event) => setPassword(event.target.value)} aria-describedby="password-hint" /><small id="password-hint" className="field-hint">At least 8 characters, including uppercase, lowercase, and a number.</small></label>
          {error && <p className="form-error" role="alert">{error}</p>}
          <button type="submit" className="primary-btn full-width" disabled={isSubmitting}>{isSubmitting ? 'Creating your account…' : 'Create account'}</button>
        </form>
      </>}
      <p className="auth-switch">Already have an account? <Link to={role ? `/signin?role=${role}` : '/signin'}>Sign in</Link></p>
    </div>
  )
}
