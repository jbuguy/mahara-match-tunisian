import { useState, type FormEvent } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'

import { API_BASE_URL, requestJson } from '../lib/api'

export function SignUpPage() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const role = searchParams.get('role')
  const [companyName, setCompanyName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [sector, setSector] = useState('')
  const [companySize, setCompanySize] = useState('1-10')
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    setIsSubmitting(true)
    try {
      await requestJson('/employers/signup', {
        method: 'POST',
        body: JSON.stringify({ company_name: companyName, email, password, sector, company_size: companySize }),
      })
      const token = await requestJson<{ access_token: string }>('/employers/login', {
        method: 'POST', body: JSON.stringify({ email, password }),
      })
      localStorage.setItem('mahara_access_token', token.access_token)
      navigate('/employer')
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Unable to create your account.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="auth-card">
      <div className="auth-intro">
        <p className="eyebrow">Create your account</p>
        <h2>{role === 'candidate' ? 'Find work that fits you' : role === 'employer' ? 'Build your hiring workspace' : 'How will you use Mahara?'}</h2>
        <p>Choose your path to set up the right workspace.</p>
      </div>

      {!role && <div className="signup-role-grid">
        <button className="signup-choice" type="button" onClick={() => setSearchParams({ role: 'candidate' })}>
          <h3>I'm looking for work</h3>
          <p>Build your profile, discover suitable jobs, and follow your next steps.</p>
          <span>Candidate account</span>
        </button>
        <button className="signup-choice" type="button" onClick={() => setSearchParams({ role: 'employer' })}>
          <h3>I'm hiring</h3>
          <p>Create clear job offers and find people with the right skills.</p>
          <span>Employer account</span>
        </button>
      </div>}

      {role && <button className="text-button" type="button" onClick={() => { setSearchParams({}); setError('') }}>
        ← Choose another path
      </button>}

      {role === 'candidate' && <section className="signup-choice signup-role-form">
        <h3>Start your candidate profile</h3>
        <p>Use your Google account. Next, choose voice onboarding, the profile assistant, or CV import.</p>
        <button className="secondary-btn full-width" type="button" onClick={() => { window.location.href = `${API_BASE_URL}/auth/google` }}>Continue with Google</button>
      </section>}

      {role === 'employer' && <form className="auth-form signup-role-form" onSubmit={handleSubmit}>
        <label><span>Company name</span><input required value={companyName} onChange={(event) => setCompanyName(event.target.value)} /></label>
        <label><span>Work email</span><input required type="email" value={email} onChange={(event) => setEmail(event.target.value)} /></label>
        <label><span>Password</span><input required type="password" minLength={8} value={password} onChange={(event) => setPassword(event.target.value)} /></label>
        <label><span>Sector</span><input required value={sector} onChange={(event) => setSector(event.target.value)} /></label>
        <label><span>Company size</span><select value={companySize} onChange={(event) => setCompanySize(event.target.value)}><option value="1-10">1–10</option><option value="11-50">11–50</option><option value="51-200">51–200</option><option value="200+">200+</option></select></label>
        {error && <p className="form-error" role="alert">{error}</p>}
        <button type="submit" className="primary-btn" disabled={isSubmitting}>{isSubmitting ? 'Creating account…' : 'Create employer account'}</button>
      </form>}

      <p className="auth-switch">Already have an account? <Link to="/signin">Sign in</Link></p>
    </div>
  )
}
