import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'

import { API_BASE_URL, requestJson } from '../lib/api'

export function SignUpPage() {
  const navigate = useNavigate()
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
      navigate('/dashboard')
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Unable to create your account.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="auth-card">
      <div className="auth-intro"><p className="eyebrow">Create account</p><h2>Join Mahara Match</h2></div>
      <section className="signup-choice">
        <h3>Looking for work?</h3>
        <p>Create your candidate account with Google.</p>
        <button className="secondary-btn full-width" type="button" onClick={() => { window.location.href = `${API_BASE_URL}/auth/google` }}>Continue with Google</button>
      </section>
      <div className="auth-divider"><span>Employer account</span></div>
      <form className="auth-form" onSubmit={handleSubmit}>
        <label><span>Company name</span><input required value={companyName} onChange={(event) => setCompanyName(event.target.value)} /></label>
        <label><span>Work email</span><input required type="email" value={email} onChange={(event) => setEmail(event.target.value)} /></label>
        <label><span>Password</span><input required type="password" minLength={8} value={password} onChange={(event) => setPassword(event.target.value)} /></label>
        <label><span>Sector</span><input required value={sector} onChange={(event) => setSector(event.target.value)} /></label>
        <label><span>Company size</span><select value={companySize} onChange={(event) => setCompanySize(event.target.value)}><option value="1-10">1–10</option><option value="11-50">11–50</option><option value="51-200">51–200</option><option value="200+">200+</option></select></label>
        {error && <p className="form-error" role="alert">{error}</p>}
        <button type="submit" className="primary-btn" disabled={isSubmitting}>{isSubmitting ? 'Creating account…' : 'Create employer account'}</button>
      </form>
    </div>
  )
}
