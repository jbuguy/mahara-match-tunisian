import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { requestJson } from '../lib/api'
import { PublicOnboardingPage } from './PublicOnboardingPage'

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

  if (!localStorage.getItem('mahara_access_token')) return <PublicOnboardingPage />

  function signOut() {
    localStorage.removeItem('mahara_access_token')
    setAccount(null)
    setLoadingAccount(false)
    window.dispatchEvent(new Event('mahara-auth-changed'))
  }

  return (
    <div className="stacked-view dashboard-workspace">
      <header className="dashboard-heading">
        <div>
          <p className="eyebrow">Espace de travail · {account?.kind ?? 'Public'}</p>
          <h2>{account ? `Bienvenue, ${account.name}` : 'Votre passerelle vers les compétences'}</h2>
          <p className="dashboard-subtitle">Un espace public tunisien pour connecter talents, employeurs et formations.</p>
        </div>
        {account ? <button className="ghost-btn" type="button" onClick={signOut}>Se déconnecter</button> : <Link className="primary-btn" to="/signup">Créer mon compte</Link>}
      </header>

      <section className="dashboard-hero">
        <div><span className="dashboard-hero-kicker">✦ MAHARA MATCH · SERVICE PUBLIC NUMÉRIQUE</span><h3>{account?.kind === 'Candidate' ? 'Construisez votre prochaine opportunité.' : 'Un marché du travail plus lisible, plus proche.'}</h3><p>{account?.kind === 'Candidate' ? 'Complétez votre profil pour recevoir des opportunités alignées sur vos savoir-faire.' : 'Retrouvez les bons outils pour avancer avec confiance dans votre parcours professionnel.'}</p></div>
        <span className="dashboard-hero-mark" aria-hidden="true">M</span>
      </section>

      <section className="detail-panel account-summary" aria-live="polite">
        <div><p className="eyebrow">Signed-in account</p><h3>{loadingAccount ? 'Checking session…' : account?.name ?? 'No active session'}</h3></div>
        {account && <div><span className="module-tag">{account.kind}</span><p>{account.email}</p>{account.kind === 'Candidate' && <small>{account.hasProfile ? 'Candidate profile complete' : 'Candidate profile setup pending'}</small>}</div>}
      </section>

      <div className="stats-grid dashboard-stats">
        <article className="metric-card">
          <span>Readiness</span>
          <strong>{health?.status ?? 'ok'}</strong>
          <small>Core platform API</small>
        </article>
        <article className="metric-card"><span>Active modules</span><strong>{modules.filter((module) => module.status === 'registered').length}</strong><small>Integrated in platform API</small></article>
      </div>

      <div className="content-grid">
        <section className="detail-panel dashboard-modules">
          <div className="section-heading"><div><p className="eyebrow">Ecosystème</p><h3>Modules disponibles</h3></div><span className="module-tag">{modules.length} services</span></div>
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
          <div className="section-heading"><div><p className="eyebrow">Prochaine étape</p><h3>Centre d’action</h3></div></div>
          <div className="action-stack">
            {loadingAccount ? <p role="status">Checking your workspace…</p> : account?.kind === 'Candidate' ? <>
              {!account.hasProfile && <Link className="secondary-btn" to="/candidate/start">Set up my profile</Link>}
              <Link className="secondary-btn" to="/candidate">{account.hasProfile ? 'Review my profile' : 'Complete my profile'}</Link>
              {account.hasProfile && <Link className="secondary-btn" to="/matches">View job matches</Link>}
              {account.hasProfile && <Link className="secondary-btn" to="/mock-interview">Practice an interview privately</Link>}
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
