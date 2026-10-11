import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { requestJson } from '../lib/api'

type HealthResponse = {
  status: string
  service: string
  environment: string
  version: string
}

type ModuleEntry = {
  code: string
  name: string
  owner: string
  description: string
  status: string
  shared_contracts: string
  contract_count: number
}

type UserSummary = { name?: string | null; email: string; has_profile?: boolean }
type EmployerSummary = { company_name: string; email: string }

export function DashboardPage({ health, modules }: { health: HealthResponse | null; modules: ModuleEntry[] }) {
  const [account, setAccount] = useState<{ name: string; email: string; kind: string; hasProfile?: boolean } | null>(null)
  const [loadingAccount, setLoadingAccount] = useState(Boolean(localStorage.getItem('mahara_access_token')))

  useEffect(() => {
    if (!localStorage.getItem('mahara_access_token')) return
    let active = true
    Promise.allSettled([
      requestJson<UserSummary>('/api/v1/me'),
      requestJson<EmployerSummary>('/employers/me'),
    ]).then(([candidate, employer]) => {
      if (!active) return
      if (candidate.status === 'fulfilled') {
        setAccount({ name: candidate.value.name || candidate.value.email, email: candidate.value.email, kind: 'Candidate', hasProfile: candidate.value.has_profile })
      } else if (employer.status === 'fulfilled') {
        setAccount({ name: employer.value.company_name, email: employer.value.email, kind: 'Employer' })
      } else {
        localStorage.removeItem('mahara_access_token')
      }
    }).finally(() => { if (active) setLoadingAccount(false) })
    return () => { active = false }
  }, [])

  function signOut() {
    localStorage.removeItem('mahara_access_token')
    setAccount(null)
    setLoadingAccount(false)
    window.dispatchEvent(new Event('mahara-auth-changed'))
  }

  return (
    <div className="stacked-view">
      <header className="panel-header">
        <div>
          <p className="eyebrow">Overview</p>
          <h2>Platform dashboard</h2>
        </div>
        {account ? <button className="ghost-btn" type="button" onClick={signOut}>Sign out</button> : <Link className="ghost-btn" to="/signin">Sign in</Link>}
      </header>

      <section className="detail-panel account-summary" aria-live="polite">
        <div><p className="eyebrow">Signed-in account</p><h3>{loadingAccount ? 'Checking session…' : account?.name ?? 'No active session'}</h3></div>
        {account && <div><span className="module-tag">{account.kind}</span><p>{account.email}</p>{account.kind === 'Candidate' && <small>{account.hasProfile ? 'Candidate profile complete' : 'Candidate profile setup pending'}</small>}</div>}
      </section>

      <div className="stats-grid">
        <article className="metric-card">
          <span>Readiness</span>
          <strong>{health?.status ?? 'ok'}</strong>
          <small>Core platform API</small>
        </article>
        <article className="metric-card"><span>Active modules</span><strong>{modules.filter((module) => module.status === 'registered').length}</strong><small>Integrated in platform API</small></article>
      </div>

      <div className="content-grid">
        <section className="detail-panel">
          <h3>Current modules</h3>
          <div className="module-list">
            {modules.map((module) => (
              <div key={module.code} className="module-item">
                <div>
                  <strong>{module.name}</strong>
                  <small>{module.description}</small>
                </div>
                <span className="module-tag">{module.status}</span>
              </div>
            ))}
          </div>
        </section>

        <section className="detail-panel">
          <h3>Action center</h3>
          <div className="action-stack">
            {loadingAccount ? <p role="status">Checking your workspace…</p> : account?.kind === 'Candidate' ? <>
              {!account.hasProfile && <Link className="secondary-btn" to="/candidate/start">Set up my profile</Link>}
              <Link className="secondary-btn" to="/candidate">{account.hasProfile ? 'Review my profile' : 'Complete my profile'}</Link>
              {account.hasProfile && <Link className="secondary-btn" to="/matches">View job matches</Link>}
            </> : account?.kind === 'Employer' ? <Link className="secondary-btn" to="/employer">Create or manage offers</Link> : <>
              <Link className="secondary-btn" to="/signup">Choose how you will use Mahara</Link>
              <Link className="ghost-btn" to="/signin">Sign in</Link>
            </>}
          </div>
        </section>
      </div>
    </div>
  )
}
