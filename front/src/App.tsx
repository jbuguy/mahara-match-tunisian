import { BrowserRouter, Link, NavLink, Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { useEffect, useState, type ReactNode } from 'react'

import { API_BASE_URL, requestJson } from './lib/api'
import { DashboardPage } from './pages/DashboardPage'
import { AuthCallbackPage } from './pages/AuthCallbackPage'
import { EmployerPage } from './pages/EmployerPage'
import { OnboardingPage } from './pages/OnboardingPage'
import { CandidatePage } from './pages/CandidatePage'
import { CandidateStartPage } from './pages/CandidateStartPage'
import { MatchesPage } from './pages/MatchesPage'
import { MockInterviewPage } from './pages/MockInterviewPage'
import { SignInPage } from './pages/SignInPage'
import { SignUpPage } from './pages/SignUpPage'
import { MinistryPage } from './pages/MinistryPage'
import { PasswordResetPage } from './pages/PasswordResetPage'
import { I18nProvider, useI18n, type Language } from './lib/i18n'

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
  const location = useLocation()
  const { language, setLanguage, t } = useI18n()
  const [notificationsOpen, setNotificationsOpen] = useState(false)
  const [account, setAccount] = useState<{ kind: 'candidate'; hasProfile: boolean } | { kind: 'employer' } | { kind: 'ministry' } | null>(null)
  const [accountLoading, setAccountLoading] = useState(true)

  useEffect(() => {
    let active = true
    async function loadAccount() {
      const token = localStorage.getItem('mahara_access_token')
      if (!token) {
        if (active) {
          setAccount(null)
          setAccountLoading(false)
        }
        return
      }
      setAccountLoading(true)
      const [roleResult] = await Promise.allSettled([requestJson<{ roles: string[] }>('/api/v1/me/roles')])
      if (!active) return
      const roles = roleResult.status === 'fulfilled' ? roleResult.value.roles : []
      if (roles.includes('ministry_admin')) setAccount({ kind: 'ministry' })
      else if (roles.includes('candidate')) {
        const [candidate] = await Promise.allSettled([requestJson<{ has_profile: boolean }>('/api/v1/me')])
        if (!active) return
        setAccount(candidate.status === 'fulfilled' ? { kind: 'candidate', hasProfile: candidate.value.has_profile } : null)
      } else if (roles.includes('employer')) setAccount({ kind: 'employer' })
      else {
        const [employer] = await Promise.allSettled([requestJson<{ email: string }>('/employers/me')])
        if (!active) return
        setAccount(employer.status === 'fulfilled' ? { kind: 'employer' } : null)
      }
      setAccountLoading(false)
    }

    void loadAccount()
    window.addEventListener('mahara-auth-changed', loadAccount)
    return () => {
      active = false
      window.removeEventListener('mahara-auth-changed', loadAccount)
    }
  }, [location.pathname])

  const isAuthPage = location.pathname === '/signin' || location.pathname === '/signup' || location.pathname === '/auth/callback'
  const cycleLanguage = () => {
    const next: Language = language === 'fr' ? 'en' : language === 'en' ? 'ar' : 'fr'
    setLanguage(next)
  }

  return (
    <main className={location.pathname === '/signup' ? 'mahara-app-shell signup-shell' : location.pathname === '/signin' ? 'mahara-app-shell signin-shell' : 'mahara-app-shell'}>
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
            {accountLoading && <span className="nav-link" role="status">{t('nav.loadingWorkspace')}</span>}
            {!accountLoading && !account && <>
              <NavLink to="/signin" className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}>{t('nav.signIn')}</NavLink>
              <NavLink to="/signup" className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}>{t('nav.createAccount')}</NavLink>
            </>}
            {!accountLoading && account?.kind === 'candidate' && <>
              <NavLink to="/dashboard" className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}>{t('nav.overview')}</NavLink>
              {!account.hasProfile && <NavLink to="/candidate/start" className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}>{t('nav.setupProfile')}</NavLink>}
              <NavLink to="/candidate" className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}>{t('nav.profile')}</NavLink>
              <NavLink to="/matches" className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}>{t('nav.matches')}</NavLink>
              <NavLink to="/mock-interview" className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}>{t('nav.interview')}</NavLink>
            </>}
            {!accountLoading && account?.kind === 'employer' && <>
              <NavLink to="/dashboard" className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}>Overview</NavLink>
              <NavLink to="/employer" className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}>Offers</NavLink>
            </>}
            {!accountLoading && account?.kind === 'ministry' && <>
              <NavLink to="/dashboard" className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}>Overview</NavLink>
              <NavLink to="/ministry" className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}>Ministry workspace</NavLink>
            </>}
          </nav>

          <div className="sidebar-panel">
            <p className="eyebrow">Platform status</p>
            {loading ? <p>{t('status.loading')}</p> : <p>{health?.status === 'ok' ? t('status.ok') : health?.status ?? 'unknown'}</p>}
          </div>
        </aside>

        <section className="main-panel">
          {!isAuthPage && <header className="product-topbar">
            <div className="product-topbar-search">
              <span aria-hidden="true">⌕</span>
              <input aria-label={t('nav.searchPlaceholder')} placeholder={t('nav.searchPlaceholder')} />
            </div>
            <div className="product-topbar-actions">
              <button className="topbar-icon-button" type="button" onClick={cycleLanguage} aria-label={t('nav.changeLanguage')} title={t('nav.changeLanguage')}>文 <span>{language.toUpperCase()}</span></button>
              <div className="notification-control"><button className="topbar-icon-button" type="button" onClick={() => setNotificationsOpen((open) => !open)} aria-label={t('nav.notifications')} aria-expanded={notificationsOpen} title={t('nav.notifications')}>♢</button>{notificationsOpen && <div className="notification-popover" role="status"><strong>{t('nav.notifications')}</strong><span>{language === 'ar' ? 'لا توجد إشعارات جديدة.' : language === 'en' ? 'No new notifications.' : 'Aucune nouvelle notification.'}</span></div>}</div>
              {account ? <span className="topbar-account"><strong>{account.kind === 'candidate' ? (language === 'ar' ? 'مترشح' : language === 'en' ? 'Candidate' : 'Candidat') : account.kind === 'employer' ? (language === 'ar' ? 'مشغّل' : language === 'en' ? 'Employer' : 'Employeur') : (language === 'ar' ? 'وزارة' : language === 'en' ? 'Ministry' : 'Ministère')}</strong><small>{t('nav.activeWorkspace')}</small></span> : <Link className="topbar-signin" to="/signin">{t('nav.signIn')}</Link>}
            </div>
          </header>}
          <Routes>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/signin" element={<SignInPage />} />
            <Route path="/signup" element={<SignUpPage />} />
            <Route path="/password-reset" element={<PasswordResetPage />} />
            <Route path="/auth/callback" element={<AuthCallbackPage />} />
            <Route path="/dashboard" element={<DashboardPage health={health} modules={modules} />} />
            <Route path="/onboarding" element={<ProtectedRoute><OnboardingPage /></ProtectedRoute>} />
            <Route path="/candidate/start" element={<ProtectedRoute><CandidateStartPage /></ProtectedRoute>} />
            <Route path="/candidate" element={<ProtectedRoute><CandidatePage /></ProtectedRoute>} />
            <Route path="/matches" element={<ProtectedRoute><MatchesPage /></ProtectedRoute>} />
            <Route path="/mock-interview" element={<ProtectedRoute><MockInterviewPage /></ProtectedRoute>} />
            <Route path="/employer" element={<ProtectedRoute><EmployerPage /></ProtectedRoute>} />
            <Route path="/ministry" element={<ProtectedRoute><MinistryPage /></ProtectedRoute>} />
          </Routes>
        </section>
      </div>
    </main>
  )
}

function ProtectedRoute({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<'checking' | 'authenticated' | 'unauthenticated'>('checking')

  useEffect(() => {
    let active = true
    const token = localStorage.getItem('mahara_access_token')
    if (!token) {
      setStatus('unauthenticated')
      return () => { active = false }
    }
    requestJson('/api/v1/me/roles')
      .then(() => { if (active) setStatus('authenticated') })
      .catch(() => {
        localStorage.removeItem('mahara_access_token')
        window.dispatchEvent(new Event('mahara-auth-changed'))
        if (active) setStatus('unauthenticated')
      })
    return () => { active = false }
  }, [])

  if (status === 'checking') return <div className="stacked-view"><p role="status">Checking your session…</p></div>
  return status === 'authenticated' ? <>{children}</> : <Navigate to="/signin" replace />
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
      <I18nProvider><PlatformShell health={health} modules={modules} loading={loading} /></I18nProvider>
    </BrowserRouter>
  )
}

export default App
