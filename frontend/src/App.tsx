import { BrowserRouter, NavLink, Navigate, Route, Routes } from 'react-router-dom'
import { useEffect, useState } from 'react'

import { API_BASE_URL } from './lib/api'
import { DashboardPage } from './pages/DashboardPage'
import { AuthCallbackPage } from './pages/AuthCallbackPage'
import { EmployerPage } from './pages/EmployerPage'
import { OnboardingPage } from './pages/OnboardingPage'
import { CandidatePage } from './pages/CandidatePage'
import { SignInPage } from './pages/SignInPage'
import { SignUpPage } from './pages/SignUpPage'

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

function PlatformShell({
  health,
  modules,
  loading,
}: {
  health: HealthResponse | null
  modules: ModuleEntry[]
  loading: boolean
}) {
  return (
    <main className="mahara-app-shell">
      <div className="app-frame">
        <aside className="sidebar">
          <div className="brand-block">
            <div className="brand-mark">M</div>
            <div>
              <p className="brand-label">Mahara</p>
              <h1>Match</h1>
            </div>
          </div>

          <nav className="sidebar-nav" aria-label="main navigation">
            <NavLink to="/signin" className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}>
              Sign in
            </NavLink>
            <NavLink to="/signup" className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}>
              Sign up
            </NavLink>
            <NavLink to="/dashboard" className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}>
              Dashboard
            </NavLink>
            <NavLink to="/onboarding" className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}>
              Onboarding agent
            </NavLink>
            <NavLink to="/candidate" className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}>
              Candidate journey
            </NavLink>
            <NavLink to="/employer" className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}>
              Employer journey
            </NavLink>
          </nav>

          <div className="sidebar-panel">
            <p className="eyebrow">Platform status</p>
            {loading ? <p>Loading…</p> : <p>{health?.status ?? 'unknown'}</p>}
          </div>
        </aside>

        <section className="main-panel">
          <Routes>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/signin" element={<SignInPage />} />
            <Route path="/signup" element={<SignUpPage />} />
            <Route path="/auth/callback" element={<AuthCallbackPage />} />
            <Route path="/dashboard" element={<DashboardPage health={health} modules={modules} />} />
            <Route path="/onboarding" element={<OnboardingPage />} />
            <Route path="/candidate" element={<CandidatePage />} />
            <Route path="/employer" element={<EmployerPage />} />
          </Routes>
        </section>
      </div>
    </main>
  )
}

function App() {
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [modules, setModules] = useState<ModuleEntry[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function loadPlatform() {
      try {
        const [healthResponse, modulesResponse] = await Promise.all([
          fetch(`${API_BASE_URL}/health`),
          fetch(`${API_BASE_URL}/platform/modules`),
        ])

        setHealth(await healthResponse.json())
        const modulesData = await modulesResponse.json()
        setModules(modulesData.modules ?? [])
      } catch {
        setHealth({ status: 'error', service: 'mahara-match', environment: 'local', version: 'unknown' })
      } finally {
        setLoading(false)
      }
    }

    loadPlatform()
  }, [])

  return (
    <BrowserRouter>
      <PlatformShell health={health} modules={modules} loading={loading} />
    </BrowserRouter>
  )
}

export default App
