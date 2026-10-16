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
  const [accountType, setAccountType] = useState<'candidate' | 'employer' | 'training_provider'>('candidate')
  const [showPassword, setShowPassword] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  async function submit(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError('')
    try {
      const token = await api<{ access_token: string }>(accountType === 'candidate' ? '/candidates/login' : accountType === 'employer' ? '/employers/login' : '/training-providers/login', { method: 'POST', body: JSON.stringify({ email, password }) })
      localStorage.setItem(TOKEN_KEY, token.access_token)
      navigate(accountType === 'candidate' ? '/candidate' : accountType === 'employer' ? '/employer' : '/training-center')
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Unable to sign in.') } finally { setBusy(false) }
  }

  return <PageFrame><div className="auth-layout">
    <section className="auth-welcome"><span className="eyebrow">AHLA W SAHLA BIKOM</span><h1>Bienvenue sur<br />Mahara Match</h1><p>Les bonnes compétences ouvrent les bonnes portes. Retrouvez votre espace et avançons ensemble.</p><div className="welcome-arch"><div className="welcome-door"><span>✦</span><strong>مهارة</strong></div></div><small>La plateforme tunisienne des talents</small></section>
    <section className="auth-card auth-card-polished">
      <div className="auth-intro"><p className="eyebrow">Accès à votre espace</p><h2>Accéder à votre compte</h2><p>Connectez-vous pour retrouver votre parcours.</p></div>
      <div className="account-kind" role="group" aria-label="Account type"><button className={accountType === 'candidate' ? 'active' : ''} onClick={() => setAccountType('candidate')} type="button">Candidat</button><button className={accountType === 'employer' ? 'active' : ''} onClick={() => setAccountType('employer')} type="button">Employeur</button><button className={accountType === 'training_provider' ? 'active' : ''} onClick={() => setAccountType('training_provider')} type="button">Centre de formation</button></div>
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
      navigate('/candidate')
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

type CandidateSkill = { code: string; label_fr: string; level: number; source: string; confidence: number | null }
type CandidateProfile = {
  full_name: string | null; email: string | null; phone: string | null; governorate: { code: string; name_fr: string } | null
  education_level: string | null; years_experience: number | null; languages: { code: string; level: string }[]
  summary: string | null; available_from: string | null; skills: CandidateSkill[]
  experiences: { job_title_raw: string; employer_name: string | null; start_date: string | null; end_date: string | null; duration_months: number | null; description: string | null }[]
  educations: { level: string | null; field_of_study: string | null; institution: string | null; graduation_year: number | null }[]
  desired_occupations: { code: string; title_fr: string; priority: number | null }[]
}
type CandidateOffer = {
  offer_id: string; title: string; description: string | null; contract_type: string; work_mode: string
  governorate_code: string | null; delegation: string | null; salary_min_tnd: number | null; salary_max_tnd: number | null
  match_score: number | null; application_status: string | null
  skills: { code: string; label_fr: string; requirement: string; min_level: number | null }[]
}
type CandidateApplication = { application_id: string; status: string; applied_at: string; job_offer: { job_offer_id: string; title: string } }
type Governorate = { code: string; name_fr: string; name_ar: string }

function CandidatePortal() {
  const navigate = useNavigate()
  const [profile, setProfile] = useState<CandidateProfile | null>(null)
  const [offers, setOffers] = useState<CandidateOffer[]>([])
  const [applications, setApplications] = useState<CandidateApplication[]>([])
  const [governorates, setGovernorates] = useState<Governorate[]>([])
  const [page, setPage] = useState<'home' | 'offers' | 'applications' | 'profile'>('home')
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState('')
  const [activeOffer, setActiveOffer] = useState<CandidateOffer | null>(null)
  const [roadmap, setRoadmap] = useState<{ status?: string; message?: string; steps?: { position: number; skill_code: string; status: string }[] } | null>(null)
  const [roadmapError, setRoadmapError] = useState('')
  const [busyOffer, setBusyOffer] = useState('')

  useEffect(() => {
    if (!localStorage.getItem(TOKEN_KEY)) { navigate('/signin', { replace: true }); return }
    void loadPortal()
  }, [navigate])

  async function loadPortal() {
    setLoading(true); setError('')
    try {
      const [me, currentProfile, currentOffers, currentApplications, regions] = await Promise.all([
        api<{ name?: string | null; email?: string }>('/api/v1/me'),
        api<CandidateProfile>('/api/v1/me/profile'),
        api<CandidateOffer[]>('/api/v1/me/offers'),
        api<CandidateApplication[]>('/api/v1/me/applications'),
        api<Governorate[]>('/api/v1/reference/governorates'),
      ])
      setProfile({ ...currentProfile, full_name: currentProfile.full_name || me.name || null, email: currentProfile.email || me.email || null })
      setOffers(currentOffers); setApplications(currentApplications); setGovernorates(regions)
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Impossible de charger votre espace.') }
    finally { setLoading(false) }
  }

  async function openOffer(offer: CandidateOffer) {
    setActiveOffer(offer); setRoadmap(null); setRoadmapError('')
    try { setRoadmap(await api<{ status?: string; message?: string; steps?: { position: number; skill_code: string; status: string }[] }>(`/api/v1/me/matches/${encodeURIComponent(offer.offer_id)}/roadmap`)) }
    catch (reason) { setRoadmapError(reason instanceof Error ? reason.message : 'Parcours indisponible.') }
  }

  async function applyToOffer(offer: CandidateOffer) {
    if (!window.confirm(`Confirmer votre candidature à « ${offer.title} » ?`)) return
    setBusyOffer(offer.offer_id)
    try {
      await api('/api/v1/me/applications', { method: 'POST', body: JSON.stringify({ job_offer_id: offer.offer_id }) })
      const [nextApplications, nextOffers] = await Promise.all([api<CandidateApplication[]>('/api/v1/me/applications'), api<CandidateOffer[]>('/api/v1/me/offers')])
      setApplications(nextApplications); setOffers(nextOffers)
      setActiveOffer(null); setMessage('Votre candidature a été envoyée.'); window.setTimeout(() => setMessage(''), 3500)
    } catch (reason) { setMessage(reason instanceof Error ? reason.message : 'La candidature n’a pas pu être envoyée.') }
    finally { setBusyOffer('') }
  }

  async function saveCandidateProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!profile) return
    const form = new FormData(event.currentTarget); setSaving(true); setMessage('')
    try {
      const payload = {
        consent: true, full_name: String(form.get('full_name') || '').trim(), email: profile.email,
        phone: String(form.get('phone') || '').trim() || null, governorate_code: String(form.get('governorate_code') || '') || null,
        education_level: profile.education_level, years_experience: String(form.get('years_experience') || '') === '' ? null : Number(form.get('years_experience')),
        languages: profile.languages || [], summary: String(form.get('summary') || '').trim() || null,
        available_from: profile.available_from, skills: profile.skills.map(({ code, level, source, confidence }) => ({ code, level, source, confidence })),
        experiences: profile.experiences.map(({ job_title_raw, employer_name, start_date, end_date, duration_months, description }) => ({ job_title_raw, employer_name, start_date, end_date, duration_months, description })),
        educations: profile.educations.map(({ level, field_of_study, institution, graduation_year }) => ({ level, field_of_study, institution, graduation_year })),
        desired_occupations: profile.desired_occupations.map((item, index) => ({ code: item.code, priority: item.priority || index + 1 })),
      }
      const updated = await api<CandidateProfile>('/api/v1/me/profile', { method: 'PUT', body: JSON.stringify(payload) })
      setProfile(updated); setMessage('Votre profil a été mis à jour.')
      setOffers(await api<CandidateOffer[]>('/api/v1/me/offers'))
    } catch (reason) { setMessage(reason instanceof Error ? reason.message : 'Le profil n’a pas pu être enregistré.') }
    finally { setSaving(false) }
  }

  const filteredOffers = offers.filter(offer => `${offer.title} ${offer.description || ''} ${offer.delegation || ''} ${offer.skills.map(skill => skill.label_fr).join(' ')}`.toLocaleLowerCase('fr').includes(search.toLocaleLowerCase('fr')))
  const appliedOfferIds = new Set(applications.map(application => application.job_offer.job_offer_id))
  const statusLabel = (status: string) => ({ submitted: 'Candidature envoyée', reviewing: 'En cours d’examen', shortlisted: 'Présélectionné', interview: 'Entretien', hired: 'Recruté', rejected: 'Clôturée', withdrawn: 'Retirée' }[status] || status)
  const offerCard = (offer: CandidateOffer) => <article className="candidate-offer-card" key={offer.offer_id}>
    <div className="candidate-offer-head"><div><span className="candidate-label">{offer.contract_type} · {offer.work_mode}</span><h3>{offer.title}</h3><p>{offer.delegation || offer.governorate_code || 'Tunisie'} · {offer.salary_min_tnd == null && offer.salary_max_tnd == null ? 'Salaire non précisé' : `${offer.salary_min_tnd ?? '—'} – ${offer.salary_max_tnd ?? '—'} TND`}</p></div><span className="candidate-match">{offer.match_score == null ? 'Nouvelle offre' : `${Math.round(offer.match_score * 100)}% match`}</span></div>
    <p className="candidate-description">{offer.description || 'Aucune description fournie.'}</p><div className="candidate-skills">{offer.skills.slice(0, 6).map(skill => <span key={skill.code}>{skill.label_fr || skill.code}</span>)}</div>
    <div className="candidate-card-actions"><button className="candidate-button secondary" onClick={() => void openOffer(offer)}>Détails et parcours</button>{appliedOfferIds.has(offer.offer_id) ? <span className="candidate-status success">Candidature envoyée</span> : <button className="candidate-button primary" disabled={busyOffer === offer.offer_id} onClick={() => void applyToOffer(offer)}>{busyOffer === offer.offer_id ? 'Envoi…' : 'Postuler'}</button>}</div>
  </article>

  function renderApplications(items: CandidateApplication[]) {
    return items.length ? <div className="candidate-timeline">{items.map(application => <article className="candidate-timeline-card" key={application.application_id}><div><h3>{application.job_offer.title}</h3><p>Envoyée le {new Date(application.applied_at).toLocaleDateString('fr-FR')}</p><small>Référence · {application.application_id}</small></div><span className="candidate-status">{statusLabel(application.status)}</span></article>)}</div> : <div className="candidate-empty">Vous n’avez pas encore de candidature. Consultez les offres correspondant à votre profil.</div>
  }

  if (loading) return <div className="candidate-loading">Chargement de votre espace candidat…</div>
  if (error) return <main className="candidate-portal"><div className="candidate-error"><h1>Votre espace n’a pas pu être chargé</h1><p>{error}</p>{error.toLowerCase().includes('profile not found') && <Link className="candidate-button primary" to="/onboarding">Compléter mon profil</Link>}<button className="candidate-button secondary" onClick={() => void loadPortal()}>Réessayer</button></div></main>
  if (!profile) return null

  return <div className="candidate-portal">
    <header className="candidate-topbar"><Link className="candidate-brand" to="/candidate"><span className="candidate-brand-mark">م</span><span>Bawaba Watania<small>Mahara Match · Espace candidat</small></span></Link><div className="candidate-account"><span>{profile.full_name || profile.email}</span><button className="candidate-button secondary" onClick={() => { localStorage.removeItem(TOKEN_KEY); navigate('/signin') }}>Déconnexion</button></div></header>
    <div className="candidate-layout"><aside className="candidate-sidebar"><section className="candidate-identity"><span className="candidate-avatar">{(profile.full_name || 'C').split(/\s+/).map(part => part[0]).join('').slice(0, 2).toUpperCase()}</span><div><strong>{profile.full_name || 'Candidat'}</strong><small>{profile.governorate?.name_fr || 'Tunisie'}</small></div></section><div className="candidate-nav-title">Mon espace</div>{([['home','Vue d’ensemble','⌂'],['offers','Opportunités','⌕'],['applications','Mes candidatures','◷'],['profile','Mon profil','◉']] as const).map(([key,label,icon]) => <button key={key} className={`candidate-nav-button ${page === key ? 'active' : ''}`} onClick={() => { setPage(key); setMessage('') }}><span>{icon}</span>{label}{key === 'offers' && <b>{offers.length}</b>}{key === 'applications' && <b>{applications.length}</b>}</button>)}<div className="candidate-sidebar-note"><strong>Votre profil</strong><p>{profile.skills.length} compétence(s) · {profile.experiences.length} expérience(s)</p><button onClick={() => setPage('profile')}>Mettre à jour →</button></div></aside>
      <main className="candidate-main">
        {message && <div className="candidate-toast" role="status">{message}</div>}
        {page === 'home' && <><div className="candidate-page-heading"><div><span className="candidate-eyebrow">Portail candidat</span><h1>Bienvenue, {profile.full_name || 'Candidat'}</h1><p>Retrouvez les opportunités et suivez vos démarches professionnelles.</p></div><button className="candidate-button primary" onClick={() => setPage('offers')}>Explorer les offres →</button></div><div className="candidate-stats"><article><span>Offres disponibles</span><strong>{offers.length}</strong></article><article><span>Candidatures envoyées</span><strong>{applications.length}</strong></article><article><span>Compétences au profil</span><strong>{profile.skills.length}</strong></article></div><section className="candidate-section"><div className="candidate-section-heading"><div><h2>Opportunités correspondant à votre profil</h2><p>Offres classées selon vos compétences et votre expérience.</p></div><button className="candidate-text-button" onClick={() => setPage('offers')}>Voir toutes</button></div>{offers.length ? <div className="candidate-offer-list">{offers.slice(0, 3).map(offerCard)}</div> : <div className="candidate-empty">Aucune offre publiée pour le moment. Revenez bientôt pour découvrir de nouvelles opportunités.</div>}</section><section className="candidate-section"><div className="candidate-section-heading"><div><h2>Dernières candidatures</h2><p>Suivez l’évolution de vos démarches.</p></div><button className="candidate-text-button" onClick={() => setPage('applications')}>Historique complet</button></div>{renderApplications(applications.slice(0, 3))}</section></>}
        {page === 'offers' && <><div className="candidate-page-heading"><div><span className="candidate-eyebrow">Emploi et compétences</span><h1>Opportunités</h1><p>Offres publiées et mises en correspondance avec votre profil.</p></div></div><label className="candidate-search">⌕ <input value={search} onChange={event => setSearch(event.target.value)} placeholder="Rechercher un métier, un lieu ou une compétence" /></label>{filteredOffers.length ? <div className="candidate-offer-list">{filteredOffers.map(offerCard)}</div> : <div className="candidate-empty">{search ? 'Aucune offre ne correspond à votre recherche.' : 'Aucune offre disponible pour le moment.'}</div>}</>}
        {page === 'applications' && <><div className="candidate-page-heading"><div><span className="candidate-eyebrow">Suivi des démarches</span><h1>Mes candidatures</h1><p>Historique des candidatures transmises aux employeurs.</p></div></div>{renderApplications(applications)}</>}
        {page === 'profile' && <><div className="candidate-page-heading"><div><span className="candidate-eyebrow">Mon espace personnel</span><h1>Mon profil professionnel</h1><p>Vos informations servent à vous proposer des opportunités pertinentes.</p></div></div><form className="candidate-section candidate-profile-form" onSubmit={saveCandidateProfile}><div className="candidate-form-grid"><label>Nom complet<input name="full_name" required maxLength={200} defaultValue={profile.full_name || ''} /></label><label>Adresse e-mail<input value={profile.email || ''} readOnly /></label><label>Téléphone<input name="phone" defaultValue={profile.phone || ''} placeholder="+216 …" /></label><label>Gouvernorat<select name="governorate_code" defaultValue={profile.governorate?.code || ''}><option value="">Non précisé</option>{governorates.map(region => <option key={region.code} value={region.code}>{region.name_fr}</option>)}</select></label><label>Années d’expérience<input name="years_experience" type="number" min="0" max="80" defaultValue={profile.years_experience ?? ''} /></label><label className="wide">Présentation professionnelle<textarea name="summary" rows={5} maxLength={2000} defaultValue={profile.summary || ''} /></label></div><button className="candidate-button primary" disabled={saving}>{saving ? 'Enregistrement…' : 'Enregistrer les modifications'}</button></form><section className="candidate-section"><div className="candidate-section-heading"><h2>Compétences déclarées</h2></div>{profile.skills.length ? profile.skills.map(skill => <div className="candidate-profile-row" key={skill.code}><span>{skill.label_fr}</span><span>Niveau {skill.level} / 4</span></div>) : <p className="candidate-muted">Aucune compétence enregistrée.</p>}</section><section className="candidate-section"><div className="candidate-section-heading"><h2>Expérience professionnelle</h2></div>{profile.experiences.length ? profile.experiences.map((experience,index) => <div className="candidate-profile-row" key={`${experience.job_title_raw}-${index}`}><span><strong>{experience.job_title_raw}</strong>{experience.employer_name ? ` · ${experience.employer_name}` : ''}</span><span>{experience.duration_months ?? '—'} mois</span></div>) : <p className="candidate-muted">Aucune expérience enregistrée.</p>}</section></>}
      </main>
    </div>
    {activeOffer && <div className="candidate-modal-backdrop" onMouseDown={event => { if (event.target === event.currentTarget) setActiveOffer(null) }}><section className="candidate-modal" role="dialog" aria-modal="true" aria-labelledby="candidate-modal-title"><div className="candidate-modal-heading"><div><span className="candidate-eyebrow">Détail de l’offre</span><h2 id="candidate-modal-title">{activeOffer.title}</h2></div><button className="candidate-close" aria-label="Fermer" onClick={() => setActiveOffer(null)}>×</button></div><p>{activeOffer.description || 'Aucune description fournie.'}</p><div className="candidate-skills">{activeOffer.skills.map(skill => <span key={skill.code}>{skill.label_fr || skill.code} · {skill.requirement}</span>)}</div><div className="candidate-roadmap"><h3>Parcours de compétences recommandé</h3>{roadmapError ? <p className="candidate-muted">Le parcours n’est pas disponible actuellement : {roadmapError}</p> : !roadmap ? <p className="candidate-muted">Chargement du parcours…</p> : roadmap.status === 'no_gap' ? <p>Votre profil correspond aux compétences demandées pour cette offre.</p> : roadmap.steps?.length ? roadmap.steps.map((step,index) => <div className="candidate-roadmap-step" key={`${step.position}-${step.skill_code}`}><span>{index + 1}</span><div><strong>{step.skill_code}</strong><small>{step.status}</small></div></div>) : <p className="candidate-muted">Aucun parcours complémentaire n’est disponible.</p>}</div><div className="candidate-card-actions"><button className="candidate-button secondary" onClick={() => setActiveOffer(null)}>Fermer</button>{appliedOfferIds.has(activeOffer.offer_id) ? <span className="candidate-status success">Candidature envoyée</span> : <button className="candidate-button primary" disabled={busyOffer === activeOffer.offer_id} onClick={() => void applyToOffer(activeOffer)}>{busyOffer === activeOffer.offer_id ? 'Envoi…' : 'Postuler'}</button>}</div></section></div>}
    <footer className="candidate-footer">Mahara Match · Plateforme tunisienne des talents</footer>
  </div>
}

type EmployerOffer = { job_offer_id: string; title: string; status: string; applications_count: number; submitted_count: number; shortlisted_count: number; hired_count: number; top_match_score: number | null; published_at: string | null }
type EmployerApplication = { application_id: string; candidate_name: string | null; candidate_email: string | null; candidate_phone: string | null; title: string; score_global: number | null; status: string; applied_at: string }
type EmployerSession = { id: string; messages: { role: 'user' | 'assistant'; content: string }[]; current_field: string | null; draft: Record<string, unknown> | null }

function EmployerPortal() {
  const navigate = useNavigate()
  const [company, setCompany] = useState<{ company_name: string; sector: string; verified: boolean } | null>(null)
  const [offers, setOffers] = useState<EmployerOffer[]>([])
  const [applications, setApplications] = useState<EmployerApplication[]>([])
  const [page, setPage] = useState<'home' | 'offers' | 'applications' | 'create'>('home')
  const [session, setSession] = useState<EmployerSession | null>(null)
  const [answer, setAnswer] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [search, setSearch] = useState('')

  useEffect(() => {
    if (!localStorage.getItem(TOKEN_KEY)) { navigate('/signin', { replace: true }); return }
    void refresh()
  }, [navigate])

  async function refresh() {
    setBusy(true); setError('')
    try {
      const [currentCompany, currentOffers, currentApplications] = await Promise.all([
        api<{ company_name: string; sector: string; verified: boolean }>('/employers/me'),
        api<EmployerOffer[]>('/api/v1/employer/offers'),
        api<EmployerApplication[]>('/api/v1/employer/applications'),
      ])
      setCompany(currentCompany); setOffers(currentOffers); setApplications(currentApplications)
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Impossible de charger votre espace recruteur.') }
    finally { setBusy(false) }
  }

  async function startOffer() {
    setError(''); setNotice(''); setSession(null); setPage('create'); setBusy(true)
    try { setSession(await api<EmployerSession>('/employer-agent/sessions', { method: 'POST', body: JSON.stringify({ mode: 'chat' }) })) }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Impossible de démarrer la création d’offre.') }
    finally { setBusy(false) }
  }

  async function sendOfferAnswer(event: FormEvent) {
    event.preventDefault(); if (!session || !answer.trim()) return
    setBusy(true); setError('')
    try {
      const updated = await api<EmployerSession>(`/employer-agent/sessions/${session.id}/messages`, { method: 'POST', body: JSON.stringify({ message: answer.trim() }) })
      setSession(updated); setAnswer('')
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Votre réponse n’a pas été enregistrée.') }
    finally { setBusy(false) }
  }

  async function publishOffer() {
    if (!session?.draft) return
    setBusy(true); setError('')
    try {
      await api(`/employer-agent/sessions/${session.id}/review`)
      await api(`/employer-agent/sessions/${session.id}/publish`, { method: 'POST' })
      setNotice('Votre offre est publiée et visible par les candidats.'); setSession(null); await refresh(); setPage('offers')
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'L’offre n’a pas pu être publiée.') }
    finally { setBusy(false) }
  }

  async function decide(application: EmployerApplication, decision: 'shortlisted' | 'hired' | 'rejected') {
    setBusy(true); setError('')
    try { await api(`/api/v1/employer/applications/${application.application_id}`, { method: 'PATCH', body: JSON.stringify({ decision }) }); await refresh() }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'La décision n’a pas pu être enregistrée.') }
    finally { setBusy(false) }
  }

  const visibleOffers = offers.filter(offer => `${offer.title} ${offer.status}`.toLocaleLowerCase('fr').includes(search.toLocaleLowerCase('fr')))
  const appCard = (application: EmployerApplication) => <article className="work-card" key={application.application_id}><div className="work-card-top"><div><span className="work-eyebrow">{application.title}</span><h3>{application.candidate_name || 'Candidat'}</h3><p>{application.candidate_email || 'Coordonnées masquées'} {application.candidate_phone ? `· ${application.candidate_phone}` : ''}</p></div><span className="work-badge">{application.score_global == null ? 'Score indisponible' : `${Math.round(application.score_global * 100)}% match`}</span></div><div className="work-actions"><span className="work-status">{application.status}</span>{!['hired','rejected'].includes(application.status) && <><button className="work-button" disabled={busy} onClick={() => void decide(application,'shortlisted')}>Présélectionner</button><button className="work-button" disabled={busy} onClick={() => void decide(application,'hired')}>Recruter</button><button className="work-button subtle" disabled={busy} onClick={() => void decide(application,'rejected')}>Clôturer</button></>}</div></article>

  if (!company && !error) return <main className="work-portal"><div className="work-loading">Chargement de l’espace recruteur…</div></main>
  if (error && !company) return <main className="work-portal"><div className="work-error"><h1>Espace recruteur indisponible</h1><p>{error}</p><button className="work-button primary" onClick={() => void refresh()}>Réessayer</button></div></main>
  return <div className="work-portal"><header className="work-header"><Link to="/employer" className="work-brand"><span>م</span><strong>Mahara Match<small>Espace recruteur</small></strong></Link><div>{company?.company_name}<button className="work-button" onClick={() => { localStorage.removeItem(TOKEN_KEY); navigate('/signin') }}>Déconnexion</button></div></header><div className="work-layout"><aside className="work-sidebar"><div className="work-company"><strong>{company?.company_name}</strong><small>{company?.sector}</small><span className={company?.verified ? 'verified' : 'unverified'}>{company?.verified ? 'Compte vérifié' : 'Vérification en attente'}</span></div>{([['home','Tableau de bord'],['offers','Mes offres'],['applications','Candidatures']] as const).map(([key,label])=><button key={key} className={page===key?'active':''} onClick={()=>setPage(key)}>{label}{key==='offers'&&<b>{offers.length}</b>}{key==='applications'&&<b>{applications.length}</b>}</button>)}<button className="work-new" onClick={() => void startOffer()}>＋ Créer une offre</button></aside><main className="work-main">{error&&<div className="work-alert" role="alert">{error}</div>}{notice&&<div className="work-success" role="status">{notice}</div>}
    {page==='home'&&<><div className="work-heading"><div><span className="work-eyebrow">Votre espace professionnel</span><h1>Bonjour, {company?.company_name}</h1><p>Publiez des offres et suivez vos candidatures au même endroit.</p></div><button className="work-button primary" onClick={()=>void startOffer()}>Créer une offre</button></div><div className="work-stats"><article><span>Offres actives</span><strong>{offers.filter(o=>o.status==='published').length}</strong></article><article><span>Candidatures reçues</span><strong>{applications.length}</strong></article><article><span>Profils présélectionnés</span><strong>{applications.filter(a=>a.status==='shortlisted').length}</strong></article></div><section className="work-section"><div className="work-section-title"><h2>Offres récentes</h2><button onClick={()=>setPage('offers')}>Voir les offres →</button></div>{offers.length?<div className="work-list">{offers.slice(0,4).map(o=><OfferSummary key={o.job_offer_id} offer={o}/>)}</div>:<div className="work-empty">Aucune offre pour le moment. Créez votre première offre pour la rendre visible aux candidats.</div>}</section><section className="work-section"><div className="work-section-title"><h2>Candidatures récentes</h2><button onClick={()=>setPage('applications')}>Tout voir →</button></div>{applications.length?<div className="work-list">{applications.slice(0,4).map(appCard)}</div>:<div className="work-empty">Les nouvelles candidatures apparaîtront ici.</div>}</section></>}
    {page==='offers'&&<><div className="work-heading"><div><span className="work-eyebrow">Recrutement</span><h1>Mes offres</h1><p>État de publication et résultats de vos offres.</p></div><button className="work-button primary" onClick={()=>void startOffer()}>＋ Nouvelle offre</button></div><label className="work-search">⌕ <input value={search} onChange={e=>setSearch(e.target.value)} placeholder="Rechercher une offre"/></label>{visibleOffers.length?<div className="work-list">{visibleOffers.map(o=><OfferSummary key={o.job_offer_id} offer={o}/>)}</div>:<div className="work-empty">Aucune offre ne correspond à votre recherche.</div>}</>}
    {page==='applications'&&<><div className="work-heading"><div><span className="work-eyebrow">Suivi de recrutement</span><h1>Candidatures</h1><p>Consultez les profils et enregistrez vos décisions de recrutement.</p></div></div>{applications.length?<div className="work-list">{applications.map(appCard)}</div>:<div className="work-empty">Aucune candidature reçue pour le moment.</div>}</>}
    {page==='create'&&<><div className="work-heading"><div><span className="work-eyebrow">Assistant de rédaction</span><h1>Créer une offre</h1><p>Répondez aux questions pour préparer une offre structurée. Vous pourrez la relire avant publication.</p></div><button className="work-button" onClick={()=>{setPage('offers');setSession(null)}}>Annuler</button></div>{!session?<div className="work-empty">{busy?'Préparation de votre assistant…':<button className="work-button primary" onClick={()=>void startOffer()}>Démarrer l’assistant</button>}</div>:<><div className="work-chat">{session.messages.map((m,i)=><div key={i} className={`work-message ${m.role}`}>{m.content}</div>)}</div>{session.draft?<section className="work-section"><h2>Relire avant publication</h2><h3>{String(session.draft.title||'Offre d’emploi')}</h3><p>{String(session.draft.description||'')}</p><p className="work-muted">L’assistant vérifie les informations et l’adéquation au référentiel avant publication.</p><button className="work-button primary" disabled={busy} onClick={()=>void publishOffer()}>{busy?'Publication…':'Vérifier et publier'}</button></section>:<form className="work-answer" onSubmit={sendOfferAnswer}><label htmlFor="offer-answer">Votre réponse</label><textarea id="offer-answer" required rows={3} value={answer} onChange={e=>setAnswer(e.target.value)} placeholder="Décrivez le poste et ses exigences…"/><button className="work-button primary" disabled={busy||!answer.trim()}>{busy?'Envoi…':'Envoyer la réponse'}</button></form>}</>}</>}
  </main></div></div>
}

function OfferSummary({ offer }: { offer: EmployerOffer }) {
  return <article className="work-card"><div className="work-card-top"><div><span className="work-eyebrow">{offer.status}</span><h3>{offer.title}</h3><p>{offer.applications_count} candidature(s) · {offer.shortlisted_count} présélectionnée(s)</p></div><span className="work-badge">{offer.top_match_score == null ? 'Pas de score' : `Meilleur match ${Math.round(offer.top_match_score*100)}%`}</span></div></article>
}

type TrainingCenter = { provider_id: string; name: string; provider_type: string; accreditation_ref: string | null; governorate: string | null; website: string | null }
type TrainingCourse = { course_id: string; title: string; description: string | null; modality: 'in_person'|'online'|'blended'; duration_hours: number | null; cost_tnd: number | null; governorate_code: string | null; language: string; certification_name: string | null; external_ref: string | null; is_active: boolean; skills: { code: string; label_fr: string; target_level: number }[] }
type TrainingSkill = { code: string; label_fr: string; skill_type: string }

function TrainingCenterPortal() {
  const navigate = useNavigate()
  const [center,setCenter]=useState<TrainingCenter|null>(null);const [courses,setCourses]=useState<TrainingCourse[]>([]);const [regions,setRegions]=useState<Governorate[]>([]);const [skills,setSkills]=useState<TrainingSkill[]>([])
  const [page,setPage]=useState<'home'|'accreditation'|'catalog'|'new'|'stats'|'settings'|'support'|'guide'>('home');const [loading,setLoading]=useState(true);const [busy,setBusy]=useState(false);const [error,setError]=useState('');const [notice,setNotice]=useState('');const [query,setQuery]=useState('');const [skillQuery,setSkillQuery]=useState('');const [selectedSkills,setSelectedSkills]=useState<{skill_code:string;target_level:number}[]>([])
  useEffect(()=>{if(!localStorage.getItem(TOKEN_KEY)){navigate('/signin',{replace:true});return}void load()},[navigate])
  async function load(){setLoading(true);setError('');try{const [provider,courseList,regionList]=await Promise.all([api<TrainingCenter>('/api/v1/training-provider/me'),api<TrainingCourse[]>('/api/v1/training-provider/courses'),api<Governorate[]>('/api/v1/reference/governorates')]);setCenter(provider);setCourses(courseList);setRegions(regionList)}catch(reason){setError(reason instanceof Error?reason.message:'Impossible de charger le centre.')}finally{setLoading(false)}}
  async function searchSkills(value:string){setSkillQuery(value);try{setSkills(await api<TrainingSkill[]>(`/api/v1/reference/skills?q=${encodeURIComponent(value)}`))}catch{setSkills([])}}
  async function createCourse(event:FormEvent<HTMLFormElement>){event.preventDefault();if(selectedSkills.length===0){setError('Ajoutez au moins une compétence du référentiel validé.');return}const form=new FormData(event.currentTarget);setBusy(true);setError('');try{await api('/api/v1/training-provider/courses',{method:'POST',body:JSON.stringify({title:String(form.get('title')),description:String(form.get('description'))||null,modality:String(form.get('modality')),duration_hours:form.get('duration_hours')?Number(form.get('duration_hours')):null,cost_tnd:form.get('cost_tnd')?Number(form.get('cost_tnd')):null,governorate_code:String(form.get('governorate_code'))||null,language:String(form.get('language')),certification_name:String(form.get('certification_name'))||null,external_ref:String(form.get('external_ref'))||null,skills:selectedSkills})});setNotice('La formation a été ajoutée au catalogue.');setPage('catalog');setSelectedSkills([]);await load()}catch(reason){setError(reason instanceof Error?reason.message:'La formation n’a pas pu être enregistrée.')}finally{setBusy(false)}}
  async function toggleCourse(course:TrainingCourse){setBusy(true);setError('');try{await api(`/api/v1/training-provider/courses/${course.course_id}/availability?is_active=${!course.is_active}`,{method:'PATCH'});await load()}catch(reason){setError(reason instanceof Error?reason.message:'La disponibilité n’a pas pu être modifiée.')}finally{setBusy(false)}}
  if(loading)return <main className="training-portal"><div className="training-empty">Chargement de l’espace du centre…</div></main>
  if(error&&!center)return <main className="training-portal"><div className="training-error"><h1>Espace centre de formation</h1><p>{error}</p>{error.toLowerCase().includes('not linked')&&<p>Votre compte doit être associé à un organisme de formation par l’administration avant d’accéder au catalogue.</p>}<button className="training-button" onClick={()=>void load()}>Réessayer</button><button className="training-button secondary" onClick={()=>{localStorage.removeItem(TOKEN_KEY);navigate('/signin')}}>Changer de compte</button></div></main>
  if(!center)return null
  const active=courses.filter(course=>course.is_active).length
  const filtered=courses.filter(course=>`${course.title} ${course.description||''} ${course.external_ref||''}`.toLocaleLowerCase('fr').includes(query.toLocaleLowerCase('fr')))
  const courseRows=(items:TrainingCourse[])=>items.length?<div className="training-course-list">{items.map(course=><article className="training-course" key={course.course_id}><div className="training-course-heading"><div><span className={`training-status ${course.is_active?'active':'offline'}`}>{course.is_active?'Visible au catalogue':'Hors ligne'}</span><h3>{course.title}</h3><p>{course.modality.replace('_',' ')} · {course.duration_hours?`${course.duration_hours} h`:'Durée à préciser'} · {course.cost_tnd===0?'Gratuite':course.cost_tnd==null?'Coût à préciser':`${course.cost_tnd} TND`}</p></div><button className="training-button secondary" disabled={busy} onClick={()=>void toggleCourse(course)}>{course.is_active?'Suspendre':'Publier'}</button></div><p className="training-description">{course.description||'Aucune description.'}</p><div className="training-tags">{course.skills.map(skill=><span key={skill.code}>{skill.label_fr} · niv. {skill.target_level}</span>)}</div></article>)}</div>:<div className="training-empty">{query?'Aucun cours ne correspond à la recherche.':'Votre catalogue est vide. Ajoutez une formation pour la proposer aux candidats.'}</div>
  return <div className="training-portal"><header className="training-header"><Link to="/training-center" className="training-brand"><span>▦</span><strong>Mahara Match<small>Portail national MFPE</small></strong></Link><div><span className="training-header-center">{center.name}</span><button className="training-button secondary" onClick={()=>{localStorage.removeItem(TOKEN_KEY);navigate('/signin')}}>Déconnexion</button></div></header><div className="training-layout"><aside className="training-sidebar"><div className="training-center-card"><div className="training-center-icon">▦</div><div><strong>{center.name}</strong><small>Centre de formation</small><span>{center.accreditation_ref?`Agrément ${center.accreditation_ref}`:'Agrément non renseigné'}</span></div></div><p className="training-nav-title">Gestion du centre</p>{([['home','Tableau de bord'],['accreditation','Vérifications & agrément'],['catalog','Catalogue de formations'],['new','Nouvelle session'],['stats','Statistiques & impact'],['settings','Paramètres du centre'],['support','Support technique'],['guide','Guide pédagogique']] as const).map(([key,label])=><button key={key} className={page===key?'active':''} onClick={()=>{setPage(key);setError('')}}>{label}{key==='catalog'&&<b>{courses.length}</b>}</button>)}<div className="training-sidebar-note">Données enregistrées dans le catalogue Mahara Match.</div></aside><main className="training-main">{error&&<div className="training-alert" role="alert">{error}</div>}{notice&&<div className="training-success" role="status">{notice}</div>}
    {page==='home'&&<><div className="training-heading"><span className="training-eyebrow">Espace organisme de formation</span><h1>Centre de formation</h1><p>Gérez les formations proposées aux candidats et consultez l’état de votre catalogue.</p></div><div className="training-stats"><article><span>Formations visibles</span><strong>{active}</strong></article><article><span>Hors ligne</span><strong>{courses.length-active}</strong></article><article><span>Références de compétences</span><strong>{courses.reduce((n,c)=>n+c.skills.length,0)}</strong></article></div><section className="training-section"><div className="training-section-head"><div><h2>Catalogue de formations</h2><p>Les cours actifs peuvent être utilisés dans les parcours de compétences.</p></div><button className="training-button" onClick={()=>{setPage('new');setNotice('')}}>＋ Ajouter une formation</button></div>{courseRows(courses.slice(0,4))}<button className="training-link" onClick={()=>setPage('catalog')}>Ouvrir le catalogue complet →</button></section><section className="training-section"><div className="training-section-head"><div><h2>Informations du centre</h2><p>Informations du compte rattaché à cet établissement.</p></div></div><div className="training-info-grid"><div><small>Organisme</small><strong>{center.name}</strong></div><div><small>Référence d’agrément</small><strong>{center.accreditation_ref||'Non renseignée'}</strong></div><div><small>Gouvernorat</small><strong>{center.governorate||'Non renseigné'}</strong></div><div><small>Site web</small><strong>{center.website||'Non renseigné'}</strong></div></div></section></>}
    {page==='catalog'&&<><div className="training-heading"><span className="training-eyebrow">Offre pédagogique</span><h1>Catalogue de formations</h1><p>Recherchez, publiez ou suspendez les cours de votre centre.</p></div><div className="training-catalog-tools"><input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Rechercher une formation"/><button className="training-button" onClick={()=>{setPage('new');setNotice('')}}>＋ Nouvelle formation</button></div>{courseRows(filtered)}</>}
    {page==='new'&&<><div className="training-heading"><span className="training-eyebrow">Publication au catalogue national</span><h1>Ajouter une formation</h1><p>Complétez la fiche de cours. Les compétences doivent correspondre au référentiel validé.</p></div><form className="training-section training-form" onSubmit={createCourse}><div className="training-form-grid"><label className="wide">Intitulé de la formation<input name="title" required minLength={3} maxLength={200}/></label><label className="wide">Description<textarea name="description" rows={4}/></label><label>Mode d’enseignement<select name="modality"><option value="in_person">Présentiel</option><option value="online">À distance</option><option value="blended">Hybride</option></select></label><label>Volume horaire<input name="duration_hours" type="number" min="1" max="5000"/></label><label>Coût (TND)<input name="cost_tnd" type="number" min="0" step="0.01"/></label><label>Gouvernorat<select name="governorate_code"><option value="">Non précisé</option>{regions.map(region=><option key={region.code} value={region.code}>{region.name_fr}</option>)}</select></label><label>Langue principale<input name="language" defaultValue="fr" maxLength={8}/></label><label>Certification délivrée<input name="certification_name" maxLength={200}/></label><label className="wide">Référence interne<input name="external_ref" maxLength={64}/></label></div><div className="training-skill-picker"><label>Ajouter des compétences du référentiel<input value={skillQuery} onChange={e=>void searchSkills(e.target.value)} placeholder="Rechercher une compétence"/></label><div className="training-skill-results">{skills.filter(skill=>!selectedSkills.some(item=>item.skill_code===skill.code)).slice(0,8).map(skill=><button type="button" key={skill.code} onClick={()=>setSelectedSkills([...selectedSkills,{skill_code:skill.code,target_level:2}])}>{skill.label_fr} <span>+</span></button>)}</div><div className="training-tags">{selectedSkills.map(item=>{const skill=skills.find(entry=>entry.code===item.skill_code);return <span key={item.skill_code}>{skill?.label_fr||item.skill_code}<select aria-label={`Niveau cible ${skill?.label_fr||item.skill_code}`} value={item.target_level} onChange={e=>setSelectedSkills(selectedSkills.map(selected=>selected.skill_code===item.skill_code?{...selected,target_level:Number(e.target.value)}:selected))}>{[1,2,3,4].map(level=><option key={level} value={level}>Niv. {level}</option>)}</select><button type="button" aria-label="Retirer" onClick={()=>setSelectedSkills(selectedSkills.filter(selected=>selected.skill_code!==item.skill_code))}>×</button></span>})}</div></div><div className="training-form-actions"><button type="button" className="training-button secondary" onClick={()=>setPage('catalog')}>Annuler</button><button className="training-button" disabled={busy}>{busy?'Enregistrement…':'Enregistrer la formation'}</button></div></form></>}
    {page==='accreditation'&&<><div className="training-heading"><span className="training-eyebrow">Conformité du centre</span><h1>Vérifications & agrément</h1><p>Consultez les références administratives enregistrées pour votre organisme.</p></div><section className="training-section"><div className="training-section-head"><h2>Référentiel de l’établissement</h2><span className="training-status active">Compte authentifié</span></div><div className="training-info-grid"><div><small>Raison sociale</small><strong>{center.name}</strong></div><div><small>Type d’organisme</small><strong>{center.provider_type}</strong></div><div><small>Référence déclarée</small><strong>{center.accreditation_ref||'Non renseignée'}</strong></div><div><small>Gouvernorat d’implantation</small><strong>{center.governorate||'Non renseigné'}</strong></div></div><p className="work-muted">Les décisions d’homologation et les recours sont gérés par l’administration. Cet espace affiche uniquement les informations liées au compte.</p></section></>}
    {page==='stats'&&<><div className="training-heading"><span className="training-eyebrow">Activité du catalogue</span><h1>Statistiques & impact</h1><p>Indicateurs calculés à partir des cours enregistrés dans votre catalogue.</p></div><div className="training-stats"><article><span>Total des formations</span><strong>{courses.length}</strong></article><article><span>Actives</span><strong>{active}</strong></article><article><span>Hors ligne</span><strong>{courses.length-active}</strong></article></div><section className="training-section"><h2>Répartition par mode d’enseignement</h2>{(['in_person','online','blended'] as const).map(modality=><div className="candidate-profile-row" key={modality}><span>{{in_person:'Présentiel',online:'À distance',blended:'Hybride'}[modality]}</span><strong>{courses.filter(course=>course.modality===modality).length}</strong></div>)}<p className="work-muted">Les inscriptions et taux de réussite ne sont pas disponibles dans les données du catalogue.</p></section></>}
    {page==='settings'&&<><div className="training-heading"><span className="training-eyebrow">Établissement</span><h1>Informations du centre</h1><p>Ces données sont gérées par l’administration de la plateforme.</p></div><section className="training-section training-info-grid"><div><small>Raison sociale</small><strong>{center.name}</strong></div><div><small>Type d’organisme</small><strong>{center.provider_type}</strong></div><div><small>Référence d’agrément</small><strong>{center.accreditation_ref||'Non renseignée'}</strong></div><div><small>Gouvernorat</small><strong>{center.governorate||'Non renseigné'}</strong></div><div><small>Portail web</small><strong>{center.website||'Non renseigné'}</strong></div><div><small>Statut du compte</small><strong>Centre rattaché au compte connecté</strong></div></section></>}
    {page==='support'&&<><div className="training-heading"><span className="training-eyebrow">Assistance</span><h1>Support technique</h1><p>Informations utiles pour utiliser l’espace de gestion du catalogue.</p></div><section className="training-section"><h2>Accès et catalogue</h2><p className="work-muted">Si votre centre n’apparaît pas, demandez à l’administration MFPE de rattacher l’organisme à votre compte. Pour les erreurs de publication, vérifiez que les compétences sélectionnées figurent dans le référentiel validé.</p><button className="training-button secondary" onClick={()=>setPage('guide')}>Consulter le guide pédagogique</button></section></>}
    {page==='guide'&&<><div className="training-heading"><span className="training-eyebrow">Ressource pédagogique</span><h1>Guide pédagogique</h1><p>Conseils pour préparer une fiche de formation claire et exploitable.</p></div><section className="training-section"><h2>Fiche de formation</h2><ol className="training-guide"><li>Donnez un titre précis au cours et décrivez les activités de formation.</li><li>Indiquez le volume horaire, le coût et le mode de suivi lorsqu’ils sont connus.</li><li>Associez au moins une compétence du référentiel et choisissez le niveau visé.</li><li>Vérifiez les informations avant de rendre le cours visible au catalogue.</li></ol><button className="training-button" onClick={()=>setPage('new')}>Ajouter une formation</button></section></>}
  </main></div><footer className="training-footer">Mahara Match · Portail national de formation professionnelle</footer></div>
}

function Welcome() {
  return <PageFrame><section className="auth-card recover-card"><p className="eyebrow">MAHARA MATCH</p><h1>Bienvenue !</h1><p>Votre compte est prêt. Vous pouvez commencer à explorer Mahara Match.</p><Link className="primary-btn button-link" to="/candidate">Ouvrir mon espace</Link><button className="secondary-btn" onClick={() => { localStorage.removeItem(TOKEN_KEY); window.location.assign('/signin') }}>Se déconnecter</button></section></PageFrame>
}

function StatusPage({ code, title, detail }: { code: string; title: string; detail: string }) {
  return <PageFrame><section className="auth-card recover-card status-card"><span className="status-code">{code}</span><p className="eyebrow">MAHARA MATCH</p><h1>{title}</h1><p>{detail}</p><Link className="primary-btn button-link" to="/signin">Retour à l’accueil</Link></section></PageFrame>
}

function AppRoutes() {
  return <Routes><Route path="/" element={<Navigate to="/signin" replace />} /><Route path="/signin" element={<SignIn />} /><Route path="/signup" element={<SignUp />} /><Route path="/recover" element={<Recover />} /><Route path="/verify-email" element={<VerifyEmail />} /><Route path="/reset-password" element={<ResetPassword />} /><Route path="/auth/callback" element={<AuthCallback />} /><Route path="/onboarding" element={<Onboarding />} /><Route path="/welcome" element={<Welcome />} /><Route path="/dashboard" element={<Navigate to="/candidate" replace />} /><Route path="/candidate" element={<CandidatePortal />} /><Route path="/employer" element={<EmployerPortal />} /><Route path="/training-center" element={<TrainingCenterPortal />} /><Route path="/access-denied" element={<StatusPage code="403" title="Accès non autorisé" detail="Ce compte ne dispose pas des autorisations nécessaires pour afficher cette page." />} /><Route path="/service-unavailable" element={<StatusPage code="503" title="Service momentanément indisponible" detail="La plateforme ne peut pas répondre pour le moment. Réessayez dans quelques instants." />} /><Route path="*" element={<StatusPage code="404" title="Cette page est introuvable" detail="Le lien a peut-être expiré ou l’adresse a été saisie incorrectement." />} /></Routes>
}

function App() { return <BrowserRouter><AppRoutes /></BrowserRouter> }

export default App
