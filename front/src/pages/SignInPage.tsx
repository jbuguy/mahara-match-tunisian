import { useState, type FormEvent } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'

import { API_BASE_URL, requestJson } from '../lib/api'
import { useI18n } from '../lib/i18n'

type Role = 'candidate' | 'employer'

export function SignInPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const requestedRole = searchParams.get('role')
  const role: Role = requestedRole === 'employer' ? 'employer' : 'candidate'
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState('')
  const { language, setLanguage, t } = useI18n()

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(''); setIsSubmitting(true)
    try {
      const token = await requestJson<{ access_token: string }>(role === 'candidate' ? '/candidates/login' : '/employers/login', { method: 'POST', body: JSON.stringify({ email, password }) })
      localStorage.setItem('mahara_access_token', token.access_token); window.dispatchEvent(new Event('mahara-auth-changed'))
      if (role === 'candidate') { const account = await requestJson<{ has_profile: boolean }>('/api/v1/me'); navigate(account.has_profile ? '/dashboard' : '/candidate/start', { replace: true }) } else navigate('/dashboard', { replace: true })
    } catch (requestError) { setError(requestError instanceof Error ? requestError.message : 'Identifiants incorrects. Veuillez réessayer.') } finally { setIsSubmitting(false) }
  }

  return <div className="signin-page">
    <header className="signin-topbar"><Link to="/signup" className="signin-government"><span className="signin-gov-mark">▣</span><strong>République Tunisienne · Écosystème Mahara Match</strong><small>Plateforme d’Insertion & Compétences</small></Link><div className="signin-standards"><span>♧ Conforme INPDP N°2024-81</span><span>☁ Souveraineté Cloud Tunisie</span></div></header>
    <main className="signin-main"><div className="signin-card">
      <aside className="signin-story"><div className="signin-story-top"><span>•••</span><span>مهارة ماتش · تونس</span><span>•••</span></div><div className="signin-story-copy"><span className="signin-story-badge">♔ ATELIER NUMÉRIQUE DE LA MÉDINA</span><h1>Ahla w Sahla b bikom</h1><h2>Bienvenue sur Mahara Match</h2><p>Le pont authentique unissant le génie artisanal tunisien, les savoir-faire techniques contemporains et les opportunités d’emploi territoriales.</p></div><div className="signin-stats"><div><strong>14 820+</strong><span>Artisans & Talents Certifiés</span><small>↗ 24 Gouvernorats</small></div><div><strong>890</strong><span>Ateliers & Entreprises</span><small>◉ Validés par UTICA / ONA</small></div></div><div className="signin-story-footer"><span>● Sessions sécurisées par signature d’État</span><small>v3.4.1 Medina Core</small></div></aside>
      <section className="signin-panel"><div className="signin-language"><div><button type="button" className={language === 'fr' ? 'selected' : ''} onClick={() => setLanguage('fr')}>Français</button><button type="button" className={language === 'en' ? 'selected' : ''} onClick={() => setLanguage('en')}>English</button><button type="button" className={language === 'ar' ? 'selected' : ''} onClick={() => setLanguage('ar')}>العربية</button></div><button type="button" onClick={() => setLanguage(language === 'ar' ? 'fr' : 'ar')}>↔ {language === 'ar' ? 'RTL' : 'LTR'}</button></div><div className="signin-notice"><b>▣</b><span><strong>Bienvenue !</strong> À la recherche d’un emploi, artisan indépendant, recruteur ou responsable d’un centre de formation ? Connectez-vous ici.</span></div><div className="signin-heading"><h2>{t('auth.signIn')}</h2><p>Saisissez vos identifiants certifiés pour gérer vos candidatures et ateliers.</p></div><form className="signin-form" onSubmit={handleSubmit}><label><span>{t('auth.email')}</span><div className="signin-input"><b>✉</b><input autoComplete="email" required type="email" placeholder="mohamed.artisan@tunsie-metiers.tn" value={email} onChange={(event) => setEmail(event.target.value)} /></div></label><label><span>{t('auth.password')} <Link to="/password-reset">{t('auth.forgotPassword')}</Link></span><div className="signin-input"><b>♙</b><input autoComplete="current-password" required type="password" value={password} onChange={(event) => setPassword(event.target.value)} /><b>◉</b></div></label><div className="signin-options"><label><input type="checkbox" defaultChecked /> Se souvenir de cet appareil (30 jours)</label><small>● TLS 1.3 Chiffré</small></div>{error && <p className="form-error" role="alert">{error}</p>}<button className="signin-submit" type="submit" disabled={isSubmitting}>{isSubmitting ? t('status.loading') : t('auth.signIn')}</button></form><div className="signin-divider"><span>OU CONTINUER VIA</span></div><button type="button" className="signin-google" onClick={() => { window.location.href = `${API_BASE_URL}/auth/google` }}><b>G</b><span>Continuer avec Google</span><small>Google Workspace⌄</small></button><button type="button" className="signin-civic">☷ <span>Plus d’options de connexion civique</span><b>⌄</b></button><div className="signin-footer-links"><span>Nouveau sur la plateforme ? <Link to={`/signup?role=${role}`}>{t('auth.signUp')}</Link></span><span>☏ Centre d’aide　·　Conditions Générales</span></div></section>
    </div></main>
  </div>
}
