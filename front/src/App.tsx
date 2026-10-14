import { FormEvent, ReactNode, useEffect, useRef, useState } from 'react'
import { BrowserRouter, Link, Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom'

const API = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'
const TOKEN_KEY = 'mahara_access_token'

async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem(TOKEN_KEY)
  const headers = new Headers(init.headers)
  if (init.body && !(init.body instanceof FormData)) headers.set('Content-Type', 'application/json')
  if (token) headers.set('Authorization', `Bearer ${token}`)
  const response = await fetch(`${API}${path}`, { ...init, headers })
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    const detail = body?.detail
    const message = typeof detail === 'string' ? detail : Array.isArray(detail) ? detail.map((item: { msg?: string }) => item.msg).join(', ') : `Request failed (${response.status})`
    throw new Error(message)
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

function BrandHeader({ onBack }: { onBack?: () => void }) {
  const [language, setLanguage] = useState('FR')
  return <header className="medina-header"><div className="medina-header-inner">
    {onBack && <button className="icon-button" type="button" onClick={onBack} aria-label="Back">←</button>}
    <Link className="medina-brand" to="/signin"><span className="medina-brand-mark">M</span><span>Mahara Match<small>منصة المهارات</small></span></Link>
    <div className="language-switch" aria-label="Language">
      {['FR', 'العربية', 'تونسي'].map((item) => <button type="button" key={item} className={language === item ? 'selected' : ''} onClick={() => setLanguage(item)}>{item}</button>)}
    </div>
  </div></header>
}

function PageFrame({ children, back }: { children: ReactNode; back?: () => void }) {
  return <><BrandHeader onBack={back} /><main className="medina-page">{children}</main><footer className="medina-footer">Mahara Match <span>•</span> فرص ومهارات أقرب إليك</footer></>
}

function SignIn() {
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [accountType, setAccountType] = useState<'candidate' | 'employer'>('candidate')
  const [showPassword, setShowPassword] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  async function submit(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError('')
    try {
      const token = await api<{ access_token: string }>(accountType === 'candidate' ? '/candidates/login' : '/employers/login', { method: 'POST', body: JSON.stringify({ email, password }) })
      localStorage.setItem(TOKEN_KEY, token.access_token)
      navigate(accountType === 'candidate' ? '/onboarding' : '/employer')
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Unable to sign in.') } finally { setBusy(false) }
  }

  return <PageFrame><div className="auth-layout">
    <section className="auth-welcome"><span className="eyebrow">AHLA W SAHLA BIKOM</span><h1>Bienvenue sur<br />Mahara Match</h1><p>Les bonnes compétences ouvrent les bonnes portes. Retrouvez votre espace et avançons ensemble.</p><div className="welcome-arch"><div className="welcome-door"><span>✦</span><strong>مهارة</strong></div></div><small>La plateforme tunisienne des talents</small></section>
    <section className="auth-card auth-card-polished">
      <div className="auth-intro"><p className="eyebrow">Accès à votre espace</p><h2>Accéder à votre compte</h2><p>Connectez-vous pour retrouver votre parcours.</p></div>
      <div className="account-kind" role="group" aria-label="Account type"><button className={accountType === 'candidate' ? 'active' : ''} onClick={() => setAccountType('candidate')} type="button">Je cherche un emploi</button><button className={accountType === 'employer' ? 'active' : ''} onClick={() => setAccountType('employer')} type="button">Je recrute</button></div>
      {error && <p className="error-box" role="alert">{error}</p>}
      {error.toLowerCase().includes('not verified') && <Link className="verify-link" to={`/verify-email?email=${encodeURIComponent(email)}`}>Renvoyer le lien de vérification</Link>}
      <form className="auth-form" onSubmit={submit}>
        <label>Adresse e-mail<input autoComplete="email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="nom@exemple.tn" /></label>
        <label><span className="label-row">Mot de passe<Link to="/recover">Mot de passe oublié ?</Link></span><span className="password-wrap"><input autoComplete="current-password" type={showPassword ? 'text' : 'password'} required value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••••••••" /><button type="button" className="password-toggle" onClick={() => setShowPassword(!showPassword)} aria-label={showPassword ? 'Hide password' : 'Show password'}>{showPassword ? 'Masquer' : 'Afficher'}</button></span></label>
        <label className="remember-row"><input type="checkbox" /> <span>Se souvenir de cet appareil</span><span className="secure-note">● Connexion sécurisée</span></label>
        <button className="primary-btn full-width" disabled={busy}>{busy ? 'Connexion…' : 'Se connecter à Mahara Match'} <span>→</span></button>
      </form>
      <div className="auth-divider"><span>ou continuer via</span></div>
      <button className="google-button" type="button" onClick={() => { window.location.href = `${API}/auth/google` }}><span className="google-g">G</span> Continuer avec Google</button>
      <p className="auth-switch">Nouveau sur la plateforme ? <Link to="/signup">Créer un compte</Link></p>
    </section>
  </div></PageFrame>
}

function SignUp() {
  const navigate = useNavigate()
  const [kind, setKind] = useState<'candidate' | 'employer' | 'staff'>('candidate')
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [company, setCompany] = useState('')
  const [sector, setSector] = useState('')
  const [size, setSize] = useState('1-10')
  const [consent, setConsent] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const strength = [password.length >= 8, /[A-Z]/.test(password), /[a-z]/.test(password), /\d/.test(password)].filter(Boolean).length

  async function submit(event: FormEvent) {
    event.preventDefault(); setError('')
    if (password !== confirm) { setError('Les mots de passe ne correspondent pas.'); return }
    if (kind === 'staff') { setError('L’activation du personnel nécessite une invitation de votre administration.'); return }
    setBusy(true)
    try {
      if (kind === 'candidate') await api('/candidates/signup', { method: 'POST', body: JSON.stringify({ full_name: name, email, password, preferred_language: 'fr', onboarding_path: 'derja_guided_voice' }) })
      else await api('/employers/signup', { method: 'POST', body: JSON.stringify({ company_name: company, email, password, sector, company_size: size }) })
      navigate(`/verify-email?email=${encodeURIComponent(email)}`)
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Unable to create this account.') } finally { setBusy(false) }
  }

  return <PageFrame><div className="signup-page">
    <div className="signup-heading"><span className="eyebrow">REJOIGNEZ MAHARA MATCH</span><h1>Rejoignez l'ecosysteme republicain des talents</h1><p>Une plateforme publique qui rapproche les personnes, les entreprises et les competences. Inscription conforme a la loi sur la protection des donnees.</p></div>
    <div className="signup-steps"><span className="current"><b>1</b> Choix du profil</span><i /><span><b>2</b> Création du compte</span><i /><span><b>3</b> Vérification e-mail</span></div>
    <section className="signup-panel"><h2>Sélectionnez la nature de votre engagement</h2><div className="role-grid">
      <button type="button" className={`role-card ${kind === 'candidate' ? 'chosen' : ''}`} onClick={() => setKind('candidate')}><span className="role-icon">↗</span><strong>Je cherche un emploi</strong><small>Candidat, artisan ou technicien</small><span className="role-action">Créer mon profil →</span></button>
      <button type="button" className={`role-card ${kind === 'employer' ? 'chosen' : ''}`} onClick={() => setKind('employer')}><span className="role-icon">⌂</span><strong>Je recrute des talents</strong><small>Entreprise, atelier ou coopérative</small><span className="role-action">Créer un espace →</span></button>
      <button type="button" className={`role-card ${kind === 'staff' ? 'chosen' : ''}`} onClick={() => setKind('staff')}><span className="role-icon">▤</span><strong>Centre ou administration</strong><small>Accès réservé sur invitation</small><span className="role-action">Activer une invitation →</span></button>
    </div>
    {kind !== 'staff' ? <form className="auth-form signup-form" onSubmit={submit}>
      <h3>{kind === 'candidate' ? 'Créer votre identifiant citoyen' : 'Créer votre espace recruteur'}</h3>
      {error && <p className="error-box" role="alert">{error}</p>}
      {kind === 'candidate' ? <label>Nom complet<input required autoComplete="name" value={name} onChange={(e) => setName(e.target.value)} placeholder="ex. Yassine Trabelsi" /></label> : <><label>Nom de l’entreprise ou de l’atelier<input required value={company} onChange={(e) => setCompany(e.target.value)} /></label><div className="two-col"><label>Secteur<input required value={sector} onChange={(e) => setSector(e.target.value)} placeholder="Artisanat, industrie…" /></label><label>Taille<select value={size} onChange={(e) => setSize(e.target.value)}><option value="1-10">1–10</option><option value="11-50">11–50</option><option value="51-200">51–200</option><option value="200+">200+</option></select></label></div></>}
      <label>Adresse e-mail<input required type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="nom@exemple.tn" /></label>
      <div className="two-col"><label>Mot de passe<input required type="password" autoComplete="new-password" value={password} onChange={(e) => setPassword(e.target.value)} minLength={8} /><small className="strength-hint">Robustesse : {['faible', 'faible', 'moyenne', 'bonne', 'forte'][strength]}</small></label><label>Confirmer le mot de passe<input required type="password" autoComplete="new-password" value={confirm} onChange={(e) => setConfirm(e.target.value)} minLength={8} /></label></div>
      <label className="consent-row"><input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} required /><span>J’accepte que mes informations soient utilisées pour créer mon compte Mahara Match et j’ai lu la politique de confidentialité.</span></label>
      <button className="primary-btn full-width" disabled={busy || !consent}>{busy ? 'Création…' : 'Créer mon compte Mahara Match'} <span>→</span></button>
    </form> : <div className="notice-box">L’activation du personnel et des centres se fait avec une invitation officielle. Contactez votre administration pour en recevoir une.</div>}
    <button className="google-button signup-google" type="button" onClick={() => { window.location.href = `${API}/auth/google` }}><span className="google-g">G</span> Continuer avec Google Workspace</button>
    <p className="auth-switch">Vous avez déjà un compte ? <Link to="/signin">Se connecter</Link></p></section>
  </div></PageFrame>
}

function Recover() {
  const [email, setEmail] = useState('')
  const [message, setMessage] = useState('')
  const [deliveryConfigured, setDeliveryConfigured] = useState<boolean | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  async function submit(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError(''); setMessage('')
    try {
      const result = await api<{ message: string; delivery_configured: boolean }>('/auth/email/password-reset/request', { method: 'POST', body: JSON.stringify({ email }) })
      setMessage(result.message); setDeliveryConfigured(result.delivery_configured)
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'La demande n’a pas pu être envoyée.') }
    finally { setBusy(false) }
  }
  return <PageFrame><section className="auth-card recover-card"><p className="eyebrow">RÉCUPÉRATION DU COMPTE</p><h1>Mot de passe oublié ?</h1><p>Indiquez l’adresse utilisée lors de la création de votre compte. Nous vous enverrons un lien s’il existe un compte avec un mot de passe pour cette adresse.</p>{error && <p className="error-box" role="alert">{error}</p>}{message && <p className="notice-box" role="status">{message}{deliveryConfigured === false && <><br />La livraison des e-mails n’est pas configurée sur cette plateforme. Contactez le support de votre organisation.</>}</p>}<form className="auth-form" onSubmit={submit}><label>Adresse e-mail<input type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} /></label><button className="primary-btn full-width" disabled={busy}>{busy ? 'Envoi…' : 'Envoyer le lien de réinitialisation'}</button></form><Link className="back-link" to="/signin">← Retour à la connexion</Link></section></PageFrame>
}

function VerifyEmail() {
  const location = useLocation()
  const navigate = useNavigate()
  const token = new URLSearchParams(location.search).get('token')
  const initialEmail = new URLSearchParams(location.search).get('email') ?? ''
  const [email, setEmail] = useState(initialEmail)
  const [message, setMessage] = useState(token ? 'Vérification de votre lien…' : '')
  const [deliveryConfigured, setDeliveryConfigured] = useState<boolean | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(Boolean(token))
  useEffect(() => {
    if (!token) return
    api<{ message: string }>('/auth/email/verification/confirm', { method: 'POST', body: JSON.stringify({ token }) })
      .then((result) => setMessage(result.message))
      .catch((reason) => { setError(reason instanceof Error ? reason.message : 'Ce lien de vérification est invalide ou expiré.'); setMessage('') })
      .finally(() => setBusy(false))
  }, [token])
  async function resend(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError(''); setMessage('')
    try {
      const result = await api<{ message: string; delivery_configured: boolean }>('/auth/email/verification/request', { method: 'POST', body: JSON.stringify({ email }) })
      setMessage(result.message); setDeliveryConfigured(result.delivery_configured)
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'La demande n’a pas pu être envoyée.') }
    finally { setBusy(false) }
  }
  const verified = Boolean(token && message && !error && !busy)
  return <PageFrame><section className="auth-card recover-card"><p className="eyebrow">VÉRIFICATION DE L’ADRESSE E-MAIL</p><h1>{verified ? 'Adresse vérifiée' : 'Vérifiez votre boîte e-mail'}</h1>{!token && <p>Votre compte est créé. Confirmez votre adresse e-mail pour pouvoir vous connecter.</p>}{busy && <p role="status">{message}</p>}{error && <p className="error-box" role="alert">{error}</p>}{message && !busy && <p className="notice-box" role="status">{message}{deliveryConfigured === false && <><br />La livraison des e-mails n’est pas configurée. Contactez le support de votre organisation.</>}</p>}{(!token || error) && <form className="auth-form" onSubmit={resend}><label>Adresse e-mail<input type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} /></label><button className="primary-btn full-width" disabled={busy}>{busy ? 'Envoi…' : 'Envoyer le lien de vérification'}</button></form>}{verified ? <button className="secondary-btn full-width" onClick={() => navigate('/signin')}>Continuer vers la connexion</button> : <Link className="back-link" to="/signin">← Retour à la connexion</Link>}</section></PageFrame>
}

function ResetPassword() {
  const location = useLocation()
  const navigate = useNavigate()
  const token = new URLSearchParams(location.search).get('token') ?? ''
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  async function submit(event: FormEvent) {
    event.preventDefault(); setError(''); setMessage('')
    if (password !== confirm) { setError('Les mots de passe ne correspondent pas.'); return }
    setBusy(true)
    try {
      const result = await api<{ message: string }>('/auth/email/password-reset/confirm', { method: 'POST', body: JSON.stringify({ token, new_password: password }) })
      setMessage(result.message)
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Ce lien de réinitialisation est invalide ou expiré.') }
    finally { setBusy(false) }
  }
  return <PageFrame><section className="auth-card recover-card"><p className="eyebrow">SÉCURITÉ DU COMPTE</p><h1>Nouveau mot de passe</h1>{!token && <p className="error-box">Le lien est incomplet. Demandez un nouveau lien de réinitialisation.</p>}{error && <p className="error-box" role="alert">{error}</p>}{message ? <><p className="notice-box" role="status">{message}</p><button className="primary-btn full-width" onClick={() => navigate('/signin')}>Se connecter</button></> : <form className="auth-form" onSubmit={submit}><label>Nouveau mot de passe<input type="password" autoComplete="new-password" required minLength={8} value={password} onChange={(e) => setPassword(e.target.value)} /><small>8 caractères minimum, avec majuscule, minuscule et chiffre.</small></label><label>Confirmer le mot de passe<input type="password" autoComplete="new-password" required minLength={8} value={confirm} onChange={(e) => setConfirm(e.target.value)} /></label><button className="primary-btn full-width" disabled={busy || !token}>{busy ? 'Mise à jour…' : 'Enregistrer le nouveau mot de passe'}</button></form>}<Link className="back-link" to="/signin">← Retour à la connexion</Link></section></PageFrame>
}

function AuthCallback() {
  const navigate = useNavigate()
  const [message, setMessage] = useState('Finalisation de votre connexion Google…')
  useEffect(() => {
    const accessToken = new URLSearchParams(window.location.hash.slice(1)).get('access_token')
    const error = new URLSearchParams(window.location.search).get('error')
    if (error || !accessToken) { setMessage('La connexion Google a échoué. Vous pouvez réessayer ou vous connecter par e-mail.'); return }
    localStorage.setItem(TOKEN_KEY, accessToken)
    api<{ has_profile: boolean }>('/api/v1/me').then(() => navigate('/onboarding', { replace: true })).catch(() => navigate('/onboarding', { replace: true }))
  }, [navigate])
  return <PageFrame><section className="auth-card recover-card"><p className="eyebrow">AUTHENTIFICATION SÉCURISÉE</p><h1>Connexion</h1><p role="status">{message}</p><Link to="/signin">Retour à la connexion</Link></section></PageFrame>
}

type AssistantUpdate = { full_name?: string | null; phone?: string | null; governorate_code?: string | null; education_level?: string | null; years_experience?: number | null; summary?: string | null; skills?: { code: string; label_fr: string; level?: number; source?: string }[] | null; experiences?: { job_title_raw: string; employer_name?: string | null; duration_months?: number | string | null; start_date?: string | null; end_date?: string | null; description?: string | null }[] | null }

function Onboarding() {
  const navigate = useNavigate()
  const [mode, setMode] = useState<'choose' | 'voice' | 'chat' | 'review'>('choose')
  const [prompt, setPrompt] = useState('Bonjour ! Quel métier exercez-vous, et quels outils utilisez-vous au quotidien ?')
  const [answer, setAnswer] = useState('')
  const [messages, setMessages] = useState<{ role: 'user' | 'assistant'; content: string }[]>([])
  const [draft, setDraft] = useState<AssistantUpdate>({})
  const [name, setName] = useState('')
  const [recording, setRecording] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [consent, setConsent] = useState(false)
  const recorder = useRef<MediaRecorder | null>(null)

  useEffect(() => {
    if (!localStorage.getItem(TOKEN_KEY)) { navigate('/signin', { replace: true }); return }
    api<{ name?: string | null }>('/api/v1/me').then((me) => { if (me.name) { setName(me.name); setDraft({ full_name: me.name }) } }).catch((reason) => setError(reason instanceof Error ? reason.message : 'Unable to load your account.'))
  }, [navigate])

  async function sendAnswer(text: string) {
    const content = text.trim(); if (!content) return
    const next = [...messages, { role: 'user' as const, content }]
    setMessages(next); setAnswer(''); setBusy(true); setError('')
    try {
      const result = await api<{ reply: string; updates: AssistantUpdate; asking?: string | null; done: boolean }>('/api/v1/me/assistant/chat', { method: 'POST', body: JSON.stringify({ messages: next, draft: { full_name: draft.full_name ?? name, phone: draft.phone ?? '', governorate_code: draft.governorate_code ?? '', education_level: draft.education_level ?? '', skills: draft.skills ?? [], experiences: draft.experiences ?? [], summary: draft.summary ?? '' } }) })
      setMessages([...next, { role: 'assistant', content: result.reply }]); setDraft((previous) => ({ ...previous, ...result.updates }))
      setPrompt(result.reply)
      if (result.done) setMode('review')
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'The assistant is temporarily unavailable.') }
    finally { setBusy(false) }
  }

  async function startRecording() {
    setError('')
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const media = new MediaRecorder(stream); recorder.current = media
      const chunks: BlobPart[] = []
      media.ondataavailable = (event) => { if (event.data.size) chunks.push(event.data) }
      media.onstop = async () => {
        stream.getTracks().forEach((track) => track.stop())
        const audio = new Blob(chunks, { type: media.mimeType || 'audio/webm' })
        const file = new File([audio], 'answer.webm', { type: audio.type })
        const form = new FormData(); form.append('file', file)
        setBusy(true)
        try { const result = await api<{ text: string }>('/api/v1/me/assistant/transcribe', { method: 'POST', body: form }); if (result.text) { setAnswer(result.text); await sendAnswer(result.text) } else setError('Aucune voix claire détectée. Réessayez ou écrivez votre réponse.') }
        catch (reason) { setError(reason instanceof Error ? reason.message : 'Transcription indisponible.') }
        finally { setBusy(false) }
      }
      media.start(); setRecording(true)
    } catch { setError('Autorisez le microphone dans votre navigateur, ou choisissez le mode écrit.'); setMode('chat') }
  }

  async function saveProfile(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError('')
    try {
      await api('/api/v1/me/profile', { method: 'PUT', body: JSON.stringify({ consent, from_cv: false, full_name: (draft.full_name || name || 'Candidat').trim(), email: null, phone: draft.phone || null, governorate_code: draft.governorate_code || null, education_level: draft.education_level || null, years_experience: draft.years_experience ?? null, summary: draft.summary || null, languages: [], skills: (draft.skills ?? []).filter((skill) => skill.code).map((skill) => ({ code: skill.code, level: skill.level ?? 2, source: skill.source ?? 'self_declared' })), experiences: (draft.experiences ?? []).filter((item) => item.job_title_raw).map((item) => ({ job_title_raw: item.job_title_raw, employer_name: item.employer_name || null, start_date: item.start_date || null, end_date: item.end_date || null, duration_months: item.duration_months ? Number(item.duration_months) : null, description: item.description || null })), educations: [], desired_occupations: [] }) })
      navigate('/dashboard')
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Unable to save your profile.') }
    finally { setBusy(false) }
  }

  return <PageFrame back={() => mode === 'choose' ? navigate('/signin') : setMode('choose')}><div className="onboarding-page">
    <div className="onboarding-topline"><span className="eyebrow">ESPACE CANDIDAT</span><span className="status-pill">● Nouveau profil</span></div>
    <div className="flow-progress"><span className={mode === 'choose' ? 'active' : 'done'}>1 <small>Choix du mode</small></span><i className={mode !== 'choose' ? 'done' : ''} /><span className={mode === 'voice' || mode === 'chat' ? 'active' : mode === 'review' ? 'done' : ''}>2 <small>Votre parcours</small></span><i className={mode === 'review' ? 'done' : ''} /><span className={mode === 'review' ? 'active' : ''}>3 <small>Révision</small></span></div>
    {error && <p className="error-box" role="alert">{error}</p>}
    {mode === 'choose' && <><div className="onboarding-heading"><p className="eyebrow">ÉTAPE 1 · MÉTHODE D’INITIATION</p><h1>Choisissez votre mode<br />de création de profil</h1><p>Parlez en derja, échangez avec l’assistant ou importez votre CV. Vous pourrez vérifier chaque information avant de l’enregistrer.</p></div><div className="onboarding-options">
      <article className="onboarding-option featured"><span className="option-badge">LE PLUS RAPIDE · 3 MIN</span><div className="option-icon">♩</div><h2>Parler avec nous</h2><p>Saisie vocale guidée en derja, arabe ou français. L’assistant structure vos compétences avec vous.</p><ul><li>✓ Répondez naturellement</li><li>✓ Vos réponses restent modifiables</li><li>✓ Idéal sur mobile</li></ul><button className="primary-btn full-width" onClick={() => setMode('voice')}>Démarrer l’entretien vocal →</button></article>
      <article className="onboarding-option"><div className="option-icon blue">✉</div><h2>Chat interactif</h2><p>Un échange écrit pas à pas, à votre rythme, avec des questions courtes.</p><ul><li>✓ Questions guidées</li><li>✓ Suggestions personnalisées</li><li>✓ Temps estimé : 6 minutes</li></ul><button className="secondary-btn full-width" onClick={() => setMode('chat')}>Lancer le chat guidé →</button></article>
      <article className="onboarding-option"><div className="option-icon olive">↑</div><h2>Importer mon CV</h2><p>Importez un CV PDF ou DOCX. Il sera analysé sans être conservé.</p><ul><li>✓ PDF ou DOCX, 5 Mo maximum</li><li>✓ Vérifiez les informations extraites</li></ul><label className="secondary-btn upload-button">Choisir un CV<input type="file" accept=".pdf,.docx" onChange={async (e) => { const file = e.target.files?.[0]; if (!file) return; const form = new FormData(); form.append('file', file); setBusy(true); try { const result = await api<{ draft: AssistantUpdate }>('/api/v1/me/cv', { method: 'POST', body: form }); setDraft((old) => ({ ...old, ...result.draft })); setMode('review') } catch (reason) { setError(reason instanceof Error ? reason.message : 'CV non reconnu.') } finally { setBusy(false) } }} /></label>{busy && <small>Analyse du CV…</small>}</article>
    </div></>}
    {(mode === 'voice' || mode === 'chat') && <section className="guided-panel"><div className="guided-header"><div><p className="eyebrow">QUESTION {messages.length + 1} · ENTRETIEN GUIDÉ</p><h1>{mode === 'voice' ? 'Parlons de votre expérience' : 'Votre assistant de profil'}</h1></div><button className="text-button" onClick={() => setMode('choose')}>Changer de mode</button></div><div className="question-box"><span>CONSIGNE DE L’ASSISTANT</span><p>{prompt}</p></div><div className="chat-transcript" aria-live="polite">{messages.map((message, i) => <div key={i} className={`conversation-message ${message.role}`}>{message.content}</div>)}{busy && <p className="chat-panel-pending">Préparation de votre réponse…</p>}</div><form className="auth-form" onSubmit={(e) => { e.preventDefault(); void sendAnswer(answer) }}><label>Votre réponse<textarea rows={4} value={answer} onChange={(e) => setAnswer(e.target.value)} placeholder="Écrivez ou dictez votre réponse…" /></label><div className="guided-actions">{mode === 'voice' && <button type="button" className={recording ? 'secondary-btn voice-recording' : 'secondary-btn'} disabled={busy} onClick={() => { if (recording && recorder.current) { recorder.current.stop(); setRecording(false) } else void startRecording() }}>{recording ? '■ Arrêter l’enregistrement' : '● Répondre à l’oral'}</button>}<button className="primary-btn" disabled={busy || !answer.trim()}>{busy ? 'Un instant…' : 'Envoyer ma réponse →'}</button></div></form><p className="privacy-note">Vos réponses sont utilisées pour préparer votre profil. Rien n’est enregistré avant votre validation.</p></section>}
    {mode === 'review' && <section className="guided-panel"><p className="eyebrow">ÉTAPE 3 · RÉVISION ET VALIDATION</p><h1>Révision de votre profil</h1><p>Modifiez les informations extraites avant de les enregistrer.</p><form className="auth-form" onSubmit={saveProfile}><label>Nom complet<input required value={draft.full_name ?? name} onChange={(e) => setDraft({ ...draft, full_name: e.target.value })} /></label><label>Résumé professionnel<textarea rows={4} value={draft.summary ?? ''} onChange={(e) => setDraft({ ...draft, summary: e.target.value })} placeholder="Présentez votre expérience et votre projet professionnel." /></label><div className="review-card"><h3>Expérience professionnelle</h3>{draft.experiences?.length ? draft.experiences.map((item, index) => <p key={index}><strong>{item.job_title_raw}</strong>{item.employer_name ? ` · ${item.employer_name}` : ''}</p>) : <p>Ajoutez votre expérience dans votre réponse ou complétez-la après cette étape.</p>}</div><div className="review-card"><h3>Compétences reconnues</h3>{draft.skills?.length ? draft.skills.map((skill, index) => <span className="skill-chip" key={index}>{skill.label_fr || skill.code}</span>) : <p>Vos compétences pourront être complétées après la création du profil.</p>}</div><label className="consent-row"><input type="checkbox" required checked={consent} onChange={(e) => setConsent(e.target.checked)} /><span>J’accepte l’utilisation de ces informations pour la mise en relation avec des offres d’emploi.</span></label>{error && <p className="error-box">{error}</p>}<button className="primary-btn full-width" disabled={busy || !consent}>{busy ? 'Enregistrement…' : 'Valider et enregistrer mon profil →'}</button></form></section>}
  </div></PageFrame>
}

function Welcome() {
  return <PageFrame><section className="auth-card recover-card"><p className="eyebrow">MAHARA MATCH</p><h1>Bienvenue !</h1><p>Votre compte est prêt. Vous pouvez commencer à explorer Mahara Match.</p><Link className="primary-btn button-link" to="/dashboard">Ouvrir mon espace</Link><button className="secondary-btn" onClick={() => { localStorage.removeItem(TOKEN_KEY); window.location.assign('/signin') }}>Se déconnecter</button></section></PageFrame>
}

function PrototypeScreen({ file }: { file: 'dashboard.html' | 'employer.html' | 'signup.html' }) {
  const location = useLocation()
  const url = `${import.meta.env.BASE_URL}${file}?view=${encodeURIComponent(location.pathname + location.search)}`
  return <main className="prototype-screen"><iframe title={file === 'employer.html' ? 'Espace employeur' : file === 'signup.html' ? 'Cr?er un compte' : 'Tableau de bord'} src={url} /></main>
}

function StatusPage({ code, title, detail }: { code: string; title: string; detail: string }) {
  return <PageFrame><section className="auth-card recover-card status-card"><span className="status-code">{code}</span><p className="eyebrow">MAHARA MATCH</p><h1>{title}</h1><p>{detail}</p><Link className="primary-btn button-link" to="/signin">Retour à l’accueil</Link></section></PageFrame>
}

function AppRoutes() {
  return <Routes><Route path="/" element={<Navigate to="/signin" replace />} /><Route path="/signin" element={<SignIn />} /><Route path="/signup" element={<PrototypeScreen file="signup.html" />} /><Route path="/recover" element={<Recover />} /><Route path="/verify-email" element={<VerifyEmail />} /><Route path="/reset-password" element={<ResetPassword />} /><Route path="/auth/callback" element={<AuthCallback />} /><Route path="/onboarding" element={<Onboarding />} /><Route path="/welcome" element={<Welcome />} /><Route path="/dashboard" element={<PrototypeScreen file="dashboard.html" />} /><Route path="/employer" element={<PrototypeScreen file="employer.html" />} /><Route path="/access-denied" element={<StatusPage code="403" title="Accès non autorisé" detail="Ce compte ne dispose pas des autorisations nécessaires pour afficher cette page." />} /><Route path="/service-unavailable" element={<StatusPage code="503" title="Service momentanément indisponible" detail="La plateforme ne peut pas répondre pour le moment. Réessayez dans quelques instants." />} /><Route path="*" element={<StatusPage code="404" title="Cette page est introuvable" detail="Le lien a peut-être expiré ou l’adresse a été saisie incorrectement." />} /></Routes>
}

function App() { return <BrowserRouter><AppRoutes /></BrowserRouter> }

export default App
