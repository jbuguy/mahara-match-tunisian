import { useEffect, useRef, useState, type FormEvent } from 'react';
import { ArrowLeft, ArrowRight, BadgeCheck, BriefcaseBusiness, Check, ChevronRight, CircleHelp, ClipboardList, FileText, GraduationCap, Home, LogOut, Menu, MessageCircle, Pencil, Plus, Send, Sparkles, UserRound, X } from 'lucide-react';
import { AuthScreen } from './AuthScreen';
import { apiRequest, explainError, type AgentSession, type InterviewMode, type OfferDraft, type OfferReview } from './api';

type WorkspaceStage = 'choose' | 'interview' | 'review';

interface EmployerAccount {
  company_name: string;
  email: string;
}

interface InterviewField {
  name: string;
  label: string;
  required: boolean;
  kind?: 'textarea' | 'select' | 'number';
  placeholder?: string;
  options?: readonly (readonly [string, string])[];
}

const interviewFields: InterviewField[] = [
  { name: 'title', label: 'Intitulé du poste', required: true, placeholder: 'Ex. Développeuse web' },
  { name: 'responsibilities', label: 'Missions principales', required: true, kind: 'textarea', placeholder: 'Décrivez le travail au quotidien…' },
  { name: 'location', label: 'Lieu de travail', required: true, placeholder: 'Gouvernorat et délégation' },
  { name: 'contract_type', label: 'Type de contrat', required: true, kind: 'select', options: [['cdi', 'CDI'], ['cdd', 'CDD'], ['sivp', 'SIVP'], ['karama', 'KARAMA'], ['internship', 'Stage'], ['freelance', 'Freelance'], ['seasonal', 'Saisonnier'], ['daily_work', 'Journalier']] },
  { name: 'required_skills', label: 'Compétences indispensables', required: true, kind: 'textarea', placeholder: 'Séparez les compétences par des virgules' },
  { name: 'preferred_skills', label: 'Compétences souhaitées', required: false, kind: 'textarea', placeholder: 'Facultatif' },
  { name: 'experience_and_education', label: 'Expérience et études', required: false, placeholder: 'Ex. 2 ans, licence en informatique' },
  { name: 'languages_required', label: 'Langues et niveaux', required: false, placeholder: 'Ex. français courant, arabe' },
  { name: 'work_mode', label: 'Organisation du travail', required: false, kind: 'select', options: [['on_site', 'Sur site'], ['remote', 'À distance'], ['hybrid', 'Hybride']] },
  { name: 'positions_count', label: 'Nombre de postes', required: false, kind: 'number', placeholder: '1' },
  { name: 'salary', label: 'Rémunération', required: false, placeholder: 'Ex. 1 400–1 800 TND par mois' },
];

export function App() {
  const [token, setToken] = useState(() => sessionStorage.getItem('employer_access_token'));
  const [loading, setLoading] = useState(Boolean(sessionStorage.getItem('employer_access_token')));
  const [session, setSession] = useState<AgentSession | null>(null);
  const [employer, setEmployer] = useState<EmployerAccount | null>(null);
  const [stage, setStage] = useState<WorkspaceStage>('choose');
  const [mode, setMode] = useState<InterviewMode>('chat');
  const [review, setReview] = useState<OfferReview | null>(null);
  const [notice, setNotice] = useState('');
  const [pending, setPending] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);

  useEffect(() => {
    if (!drawerOpen) return;
    function closeOnEscape(event: KeyboardEvent) {
      if (event.key === 'Escape') setDrawerOpen(false);
    }
    window.addEventListener('keydown', closeOnEscape);
    return () => window.removeEventListener('keydown', closeOnEscape);
  }, [drawerOpen]);

  useEffect(() => {
    if (!token) {
      setLoading(false);
      return;
    }
    let active = true;
    setLoading(true);
    void apiRequest<EmployerAccount>('/employers/me', token)
      .then((profile) => { if (active) setEmployer(profile); })
      .catch(() => {});
    apiRequest<AgentSession[]>('/employer-agent/sessions', token)
      .then((sessions) => {
        if (!active) return;
        const latest = sessions.find((item) => !item.complete) ?? sessions[0];
        if (latest) void openSession(latest, token);
      })
      .catch(() => {
        if (!active) return;
        sessionStorage.removeItem('employer_access_token');
        setToken(null);
      })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [token]);

  async function openSession(item: AgentSession, activeToken = token) {
    if (!activeToken) return;
    setSession(item);
    setMode(item.mode);
    if (item.draft || item.complete) {
      setStage('review');
      if (item.draft) {
        try {
          setReview(await apiRequest<OfferReview>(`/employer-agent/sessions/${item.id}/review`, activeToken));
        } catch (error) {
          setNotice(explainError(error));
        }
      } else {
        setReview(null);
      }
    } else {
      setReview(null);
      setStage('interview');
    }
  }

  async function authenticate(accessToken: string) {
    sessionStorage.setItem('employer_access_token', accessToken);
    setToken(accessToken);
    setEmployer(null);
    setSession(null);
    setStage('choose');
  }

  function signOut() {
    sessionStorage.removeItem('employer_access_token');
    setToken(null);
    setEmployer(null);
    setSession(null);
    setReview(null);
    setStage('choose');
    setNotice('');
    setDrawerOpen(false);
  }

  function selectNavigation(label: string) {
    setDrawerOpen(false);
    if (label === 'Offres') {
      newOffer();
      return;
    }
    setNotice(`${label} : bientôt disponible.`);
  }

  async function startSession() {
    if (!token) return;
    setPending(true);
    setNotice('');
    try {
      const created = await apiRequest<AgentSession>('/employer-agent/sessions', token, {
        method: 'POST',
        body: JSON.stringify({ mode }),
      });
      setSession(created);
      setStage('interview');
    } catch (error) {
      setNotice(explainError(error));
    } finally {
      setPending(false);
    }
  }

  function newOffer() {
    setSession(null);
    setReview(null);
    setNotice('');
    setMode('chat');
    setStage('choose');
  }

  const accountName = employer?.company_name || 'Recruteur';
  const accountInitials = employer
    ? employer.company_name.split(/\s+/).slice(0, 2).map((word) => word[0]).join('').toUpperCase()
    : 'ER';

  if (!token) return <AuthScreen onAuthenticated={authenticate} />;
  if (loading) return <div className="loading-screen"><span className="loading-orbit" /><p>Ouverture de votre espace…</p></div>;

  return (
    <div className="app-shell">
      {drawerOpen && <>
        <button className="drawer-backdrop" type="button" aria-label="Fermer le menu" onClick={() => setDrawerOpen(false)} />
        <aside className="mobile-drawer" role="dialog" aria-modal="true" aria-label="Navigation principale">
          <div className="drawer-heading"><a className="brand-lockup" href="#workspace" onClick={(event) => { event.preventDefault(); selectNavigation('Offres'); }}><span className="brand-mark"><BriefcaseBusiness size={18} /></span><span>Mahara</span></a><button className="icon-action" type="button" aria-label="Fermer le menu" onClick={() => setDrawerOpen(false)}><X size={18} /></button></div>
          <EmployerNavigation onSelect={selectNavigation} />
        </aside>
      </>}
      <aside className="desktop-sidebar">
        <a className="brand-lockup" href="#workspace" onClick={(event) => { event.preventDefault(); selectNavigation('Offres'); }}><span className="brand-mark"><BriefcaseBusiness size={18} /></span><span>Mahara</span></a>
        <EmployerNavigation onSelect={selectNavigation} />
      </aside>
      <div className="app-content">
        <header className="app-header">
          <button className="mobile-menu-button" type="button" aria-label="Ouvrir le menu" aria-expanded={drawerOpen} onClick={() => setDrawerOpen(true)}><Menu size={21} /></button>
          <span className="mobile-brand"><span className="brand-mark"><BriefcaseBusiness size={17} /></span>Mahara</span>
          <h1 className="page-title">Offres</h1>
          <div className="header-actions">
            {session && <span className="session-chip"><span className="live-dot" />{stage === 'review' ? 'Brouillon à relire' : 'Offre en cours'}</span>}
            <details className="account-menu"><summary><span className="account-avatar">{accountInitials}</span><span className="account-copy"><strong>{accountName}</strong><small>{employer?.email ?? 'Espace entreprise'}</small></span></summary><div className="account-popover"><button type="button" onClick={signOut}><LogOut size={16} />Se déconnecter</button></div></details>
          </div>
        </header>
        <main className="workspace" id="workspace">
        {notice && <div className="notice" role="status"><CircleHelp size={17} />{notice}<button type="button" aria-label="Fermer" onClick={() => setNotice('')}><X size={16} /></button></div>}
        {stage === 'choose' && <ModePicker mode={mode} setMode={setMode} onStart={startSession} pending={pending} />}
        {stage === 'interview' && session && token && <InterviewWorkspace
          session={session}
          token={token}
          pending={pending}
          setPending={setPending}
          onSession={(updated) => void openSession(updated)}
          onNotice={setNotice}
          onBack={newOffer}
        />}
        {stage === 'review' && session?.draft && token && <OfferReviewWorkspace
          session={session}
          initialReview={review}
          token={token}
          onNotice={setNotice}
          onSaved={(updated, updatedReview) => { setSession(updated); setReview(updatedReview); }}
          onNewOffer={newOffer}
        />}
        {stage === 'review' && session && !session.draft && <section className="generation-state"><CircleHelp size={24} /><h1>Le brouillon n'est pas encore disponible</h1><p>Les réponses sont conservées dans cette session. Vous pouvez démarrer une nouvelle offre pendant que le référentiel est vérifié.</p><button className="button-primary" type="button" onClick={newOffer}>Commencer une autre offre <ArrowRight size={16} /></button></section>}
        </main>
      </div>
    </div>
  );
}

function EmployerNavigation({ onSelect }: { onSelect: (label: string) => void }) {
  const items = [
    { label: 'Accueil', icon: Home },
    { label: 'Offres', icon: BriefcaseBusiness },
    { label: 'Candidatures', icon: ClipboardList },
    { label: 'Formation', icon: GraduationCap },
    { label: 'Profil', icon: UserRound },
  ];
  return <nav className="primary-navigation" aria-label="Navigation principale"><span className="navigation-caption">ESPACE RECRUTEUR</span>{items.map(({ label, icon: Icon }) => <button className={`navigation-item ${label === 'Offres' ? 'active' : ''}`} type="button" key={label} aria-current={label === 'Offres' ? 'page' : undefined} onClick={() => onSelect(label)}><Icon size={18} /><span>{label}</span>{label !== 'Offres' && <small>Bientôt</small>}</button>)}</nav>;
}

function ModePicker({ mode, setMode, onStart, pending }: { mode: InterviewMode; setMode: (mode: InterviewMode) => void; onStart: () => void; pending: boolean }) {
  return (
    <section className="mode-page">
      <div className="workspace-kicker"><span>ESPACE RECRUTEUR</span><span>01 / PRÉPARATION</span></div>
      <div className="mode-intro"><p className="eyebrow">Une offre, à votre rythme</p><h1>Comment souhaitez-vous construire votre offre&nbsp;?</h1><p>Dans les deux cas, vous pourrez relire et ajuster le brouillon avant de l'utiliser.</p></div>
      <div className="mode-grid" role="radiogroup" aria-label="Choix du parcours de création">
        <button className={`mode-card ${mode === 'chat' ? 'selected' : ''}`} type="button" role="radio" aria-checked={mode === 'chat'} onClick={() => setMode('chat')}>
          <span className="mode-icon coral"><MessageCircle size={22} /></span><span className="mode-label">GUIDÉ · CONVERSATION</span><strong>Une question à la fois</strong><span className="mode-copy">Répondez librement en français ou en derja. L'assistant vous accompagne et peut clarifier vos réponses.</span><span className="mode-example"><span>EXEMPLE</span><i>« Quelles seront les missions principales&nbsp;? »</i></span><span className="radio-indicator"><Check size={13} /></span>
        </button>
        <button className={`mode-card ${mode === 'form' ? 'selected' : ''}`} type="button" role="radio" aria-checked={mode === 'form'} onClick={() => setMode('form')}>
          <span className="mode-icon green"><FileText size={22} /></span><span className="mode-label">DIRECT · STRUCTURÉ</span><strong>Tous les détails, d'un coup</strong><span className="mode-copy">Renseignez les champs à votre rythme, vérifiez vos réponses, puis générez le brouillon.</span><span className="mode-example"><span>APERÇU</span><i>Poste · missions · lieu · compétences…</i></span><span className="radio-indicator"><Check size={13} /></span>
        </button>
      </div>
      <div className="mode-footer"><span><Sparkles size={15} /> Aucune réponse n'est publiée sans votre validation.</span><button className="button-primary" type="button" onClick={onStart} disabled={pending}>{pending ? 'Préparation…' : 'Commencer'}<ArrowRight size={17} /></button></div>
    </section>
  );
}

function InterviewWorkspace({ session, token, pending, setPending, onSession, onNotice, onBack }: {
  session: AgentSession;
  token: string;
  pending: boolean;
  setPending: (pending: boolean) => void;
  onSession: (session: AgentSession) => void;
  onNotice: (message: string) => void;
  onBack: () => void;
}) {
  const [reply, setReply] = useState('');
  const [answers, setAnswers] = useState<Record<string, string>>(session.answers ?? {});
  const [formReview, setFormReview] = useState(false);
  const messagesEnd = useRef<HTMLDivElement>(null);

  useEffect(() => { messagesEnd.current?.scrollIntoView({ behavior: 'smooth', block: 'end' }); }, [session.messages.length]);
  useEffect(() => { setAnswers(session.answers ?? {}); }, [session.id]);

  async function sendMessage(message: string) {
    if (!message.trim()) return;
    setPending(true);
    onNotice('');
    setReply('');
    try {
      const updated = await apiRequest<AgentSession>(`/employer-agent/sessions/${session.id}/messages`, token, {
        method: 'POST', body: JSON.stringify({ message: message.trim() }),
      });
      onSession(updated);
    } catch (error) {
      onNotice(explainError(error));
      setReply(message);
    } finally {
      setPending(false);
    }
  }

  async function submitForm() {
    const missing = interviewFields.filter((field) => field.required && !answers[field.name]?.trim());
    if (missing.length) {
      onNotice(`À renseigner : ${missing.map((field) => field.label.toLowerCase()).join(', ')}.`);
      setFormReview(false);
      return;
    }
    setPending(true);
    onNotice('');
    try {
      const updated = await apiRequest<AgentSession>(`/employer-agent/sessions/${session.id}/answers`, token, {
        method: 'POST', body: JSON.stringify({ answers }),
      });
      onSession(updated);
    } catch (error) {
      onNotice(explainError(error));
      setFormReview(false);
    } finally {
      setPending(false);
    }
  }

  const fieldIndex = session.current_field ? interviewFields.findIndex((field) => field.name === session.current_field) : interviewFields.length;
  const progress = Math.min(100, Math.round((Math.max(0, fieldIndex) / interviewFields.length) * 100));

  return (
    <section className={`interview-page ${session.mode === 'form' ? 'form-page' : ''}`}>
      <div className="workspace-kicker"><button className="back-link" type="button" onClick={onBack}><ArrowLeft size={15} /> Parcours</button><span>{session.mode === 'chat' ? '02 / ENTRETIEN GUIDÉ' : '02 / FORMULAIRE'}</span></div>
      <div className="interview-heading"><div><p className="eyebrow">{session.mode === 'chat' ? 'Votre assistant de rédaction' : 'Votre offre, en quelques champs'}</p><h1>{session.mode === 'chat' ? 'Construisons votre offre ensemble.' : formReview ? 'Vérifiez vos réponses.' : 'Parlons du poste à pourvoir.'}</h1></div><span className="progress-count">{session.mode === 'chat' ? `${Math.max(1, fieldIndex + 1)} / ${interviewFields.length}` : `${Object.values(answers).filter(Boolean).length} réponses`}</span></div>
      <div className="progress-track"><span style={{ width: `${session.mode === 'chat' ? progress : Math.round((Object.values(answers).filter(Boolean).length / interviewFields.length) * 100)}%` }} /></div>
      {session.mode === 'chat' ? <>
        <div className="chat-transcript" aria-live="polite" aria-label="Conversation">
          {session.messages.map((message, index) => <article key={`${index}-${message.role}`} className={`chat-message ${message.role}`}>
            <span className="message-avatar">{message.role === 'assistant' ? <Sparkles size={15} /> : 'VOUS'}</span><div className="message-body"><span className="message-author">{message.role === 'assistant' ? 'Mahara · assistant' : 'Votre réponse'}</span><p>{message.content}</p></div>
          </article>)}
          {pending && <div className="typing-indicator" aria-label="Réponse en cours"><span /><span /><span /></div>}
          <div ref={messagesEnd} />
        </div>
        <form className="chat-composer" onSubmit={(event: FormEvent) => { event.preventDefault(); void sendMessage(reply); }}>
          <label className="sr-only" htmlFor="chat-reply">Votre réponse</label><textarea id="chat-reply" value={reply} onChange={(event) => setReply(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); void sendMessage(reply); } }} placeholder="Écrivez en français ou en derja…" disabled={pending} />
          <div className="composer-tools"><span>Entrée pour envoyer · Maj + Entrée pour aller à la ligne</span><div>{session.current_field && !['title', 'responsibilities', 'location', 'contract_type', 'required_skills'].includes(session.current_field) && <button className="skip-button" type="button" disabled={pending} onClick={() => void sendMessage('skip')}>Passer cette question</button>}<button className="send-button" type="submit" aria-label="Envoyer la réponse" disabled={pending || !reply.trim()}><Send size={17} /></button></div></div>
        </form>
      </> : <>
        {formReview ? <div className="form-review-list">{interviewFields.map((field) => <div key={field.name} className="form-review-row"><span>{field.label}{field.required && <i> · obligatoire</i>}</span><strong>{answers[field.name]?.trim() || 'Non renseigné'}</strong></div>)}</div> : <div className="question-form-grid">{interviewFields.map((field) => <label className={`question-field ${field.kind === 'textarea' ? 'wide' : ''}`} key={field.name}>{field.label}<span className={field.required ? 'required-cue' : 'optional-cue'}>{field.required ? 'Obligatoire' : 'Facultatif'}</span>
          {field.kind === 'textarea' ? <textarea value={answers[field.name] ?? ''} placeholder={field.placeholder} onChange={(event) => setAnswers({ ...answers, [field.name]: event.target.value })} /> : field.kind === 'select' ? <select value={answers[field.name] ?? ''} onChange={(event) => setAnswers({ ...answers, [field.name]: event.target.value })}><option value="">Choisir…</option>{field.options?.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select> : <input type={field.kind === 'number' ? 'number' : 'text'} min={field.kind === 'number' ? 1 : undefined} value={answers[field.name] ?? ''} placeholder={field.placeholder} onChange={(event) => setAnswers({ ...answers, [field.name]: event.target.value })} />}
        </label>)}</div>}
        <div className="form-actions"><button className="text-button" type="button" onClick={() => setFormReview(!formReview)}>{formReview ? <><Pencil size={15} /> Modifier mes réponses</> : <>Vérifier mes réponses <ArrowRight size={16} /></>}</button>{formReview && <button className="button-primary" type="button" disabled={pending} onClick={() => void submitForm()}>{pending ? 'Création du brouillon…' : 'Générer mon brouillon'}<Sparkles size={16} /></button>}</div>
      </>}
    </section>
  );
}

function OfferReviewWorkspace({ session, initialReview, token, onNotice, onSaved, onNewOffer }: {
  session: AgentSession;
  initialReview: OfferReview | null;
  token: string;
  onNotice: (message: string) => void;
  onSaved: (session: AgentSession, review: OfferReview) => void;
  onNewOffer: () => void;
}) {
  const [draft, setDraft] = useState<OfferDraft>(session.draft!);
  const [review, setReview] = useState<OfferReview | null>(initialReview);
  const [pending, setPending] = useState(false);
  const [saved, setSaved] = useState(false);
  const [dismissed, setDismissed] = useState<string[]>([]);

  useEffect(() => { setDraft(session.draft!); setReview(initialReview); }, [session.id, session.draft, initialReview]);

  async function saveDraft(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    setSaved(false);
    onNotice('');
    try {
      const updated = await apiRequest<AgentSession>(`/employer-agent/sessions/${session.id}/draft`, token, {
        method: 'PATCH', body: JSON.stringify({ draft }),
      });
      const updatedReview = await apiRequest<OfferReview>(`/employer-agent/sessions/${session.id}/review`, token);
      setDraft(updated.draft!);
      setReview(updatedReview);
      onSaved(updated, updatedReview);
      setSaved(true);
    } catch (error) {
      onNotice(explainError(error));
    } finally {
      setPending(false);
    }
  }

  function update<K extends keyof OfferDraft>(key: K, value: OfferDraft[K]) {
    setDraft({ ...draft, [key]: value });
  }

  function focusField(field: string) {
    document.getElementById(`review-${field}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    document.getElementById(`review-${field}`)?.focus({ preventScroll: true });
  }

  return (
    <section className="review-page">
      <div className="workspace-kicker"><span>03 / VOTRE BROUILLON</span><button className="back-link" type="button" onClick={onNewOffer}><Plus size={15} /> Nouvelle offre</button></div>
      <div className="review-heading"><div><p className="eyebrow"><BadgeCheck size={15} /> Première version prête</p><h1>Une offre claire attire les bonnes candidatures.</h1><p>Relisez les détails et ajustez-les avant de réutiliser votre brouillon.</p></div><span className="draft-stamp">BROUILLON<br />NON PUBLIÉ</span></div>
      <div className="review-layout">
        <form className="offer-editor" onSubmit={saveDraft}>
          <div className="editor-section-heading"><span>01</span><div><h2>Le poste</h2><p>Les informations principales de l'offre</p></div></div>
          <label className="editor-field">Intitulé<input id="review-title" value={draft.title} onChange={(event) => update('title', event.target.value)} required minLength={3} /></label>
          <label className="editor-field">Missions<textarea id="review-description" value={draft.description} onChange={(event) => update('description', event.target.value)} required minLength={10} rows={4} /></label>
          <div className="editor-grid">
            <label className="editor-field">Contrat<select value={draft.contract_type} onChange={(event) => update('contract_type', event.target.value)}>{[['cdi', 'CDI'], ['cdd', 'CDD'], ['sivp', 'SIVP'], ['karama', 'KARAMA'], ['internship', 'Stage'], ['freelance', 'Freelance'], ['seasonal', 'Saisonnier'], ['daily_work', 'Journalier']].map(([value, label]) => <option value={value} key={value}>{label}</option>)}</select></label>
            <label className="editor-field">Mode<select value={draft.work_mode} onChange={(event) => update('work_mode', event.target.value)}><option value="on_site">Sur site</option><option value="remote">À distance</option><option value="hybrid">Hybride</option></select></label>
            <label className="editor-field">Gouvernorat (code)<input value={draft.location.governorate_code} onChange={(event) => update('location', { ...draft.location, governorate_code: event.target.value })} required /></label>
            <label className="editor-field">Délégation<input value={draft.location.delegation ?? ''} onChange={(event) => update('location', { ...draft.location, delegation: event.target.value || null })} /></label>
            <label className="editor-field">Expérience minimale (années)<input id="review-min_years_experience" type="number" min="0" max="40" step="0.5" value={draft.min_years_experience} onChange={(event) => update('min_years_experience', Number(event.target.value))} /></label>
            <label className="editor-field">Nombre de postes<input type="number" min="1" max="1000" value={draft.positions_count} onChange={(event) => update('positions_count', Number(event.target.value))} /></label>
          </div>
          <label className="editor-field">Niveau d'études minimum<select id="review-education_level_min" value={draft.education_level_min ?? ''} onChange={(event) => update('education_level_min', event.target.value || null)}><option value="">Non précisé</option>{[['primary', 'Primaire'], ['lower_secondary', 'Collège'], ['baccalaureate', 'Baccalauréat'], ['vocational_cap', 'CAP'], ['vocational_btp', 'BTP'], ['vocational_bts', 'BTS'], ['licence', 'Licence'], ['master', 'Master'], ['engineer', 'Ingénieur'], ['doctorate', 'Doctorat']].map(([value, label]) => <option value={value} key={value}>{label}</option>)}</select></label>
          <div className="editor-section-heading separated"><span>02</span><div><h2>Compétences</h2><p>Codes validés dans le référentiel Mahara</p></div></div>
          <div className="skill-editor" id="review-skills">{draft.skills.map((skill, index) => <div className="skill-edit-row" key={`${skill.skill_code}-${index}`}><span className="skill-code">{skill.skill_code}</span><select aria-label={`Importance de ${skill.skill_code}`} value={skill.requirement} onChange={(event) => update('skills', draft.skills.map((item, itemIndex) => itemIndex === index ? { ...item, requirement: event.target.value as 'required' | 'preferred' } : item))}><option value="required">Indispensable</option><option value="preferred">Souhaitée</option></select><select aria-label={`Niveau de ${skill.skill_code}`} value={skill.min_level} onChange={(event) => update('skills', draft.skills.map((item, itemIndex) => itemIndex === index ? { ...item, min_level: Number(event.target.value) } : item))}>{[1, 2, 3, 4].map((level) => <option key={level} value={level}>Niveau {level}</option>)}</select></div>)}</div>
          <div className="editor-section-heading separated"><span>03</span><div><h2>Langues</h2><p>Langues et niveaux attendus</p></div></div>
          <div className="skill-editor" id="review-languages">{draft.languages_required.map((language, index) => <div className="skill-edit-row" key={`${language.code}-${index}`}><select aria-label={`Langue ${index + 1}`} value={language.code} onChange={(event) => update('languages_required', draft.languages_required.map((item, itemIndex) => itemIndex === index ? { ...item, code: event.target.value } : item))}><option value="ar-TN">Arabe tunisien</option><option value="fr">Français</option><option value="en">Anglais</option><option value="ar">Arabe</option></select><select aria-label={`Niveau de langue ${index + 1}`} value={language.level} onChange={(event) => update('languages_required', draft.languages_required.map((item, itemIndex) => itemIndex === index ? { ...item, level: Number(event.target.value) } : item))}>{[1, 2, 3, 4].map((level) => <option key={level} value={level}>Niveau {level}</option>)}</select><button className="icon-action" type="button" aria-label="Retirer cette langue" onClick={() => update('languages_required', draft.languages_required.filter((_, itemIndex) => itemIndex !== index))}><X size={15} /></button></div>)}</div>
          <button className="text-button salary-add" type="button" onClick={() => update('languages_required', [...draft.languages_required, { code: 'fr', level: 2 }])}><Plus size={16} /> Ajouter une langue</button>
          <div className="editor-section-heading separated"><span>04</span><div><h2>Rémunération</h2><p>Indiquez une fourchette si elle est définie</p></div></div>
          {draft.salary ? <div className="salary-editor" id="review-salary"><label className="editor-field">Minimum (TND)<input type="number" min="0" step="0.01" value={draft.salary.min_tnd ?? ''} onChange={(event) => update('salary', { ...draft.salary!, min_tnd: event.target.value ? Number(event.target.value) : null })} /></label><label className="editor-field">Maximum (TND)<input type="number" min="0" step="0.01" value={draft.salary.max_tnd ?? ''} onChange={(event) => update('salary', { ...draft.salary!, max_tnd: event.target.value ? Number(event.target.value) : null })} /></label><label className="editor-field">Période<select value={draft.salary.period} onChange={(event) => update('salary', { ...draft.salary!, period: event.target.value as 'hour' | 'day' | 'month' })}><option value="hour">Par heure</option><option value="day">Par jour</option><option value="month">Par mois</option></select></label></div> : <button className="text-button salary-add" type="button" id="review-salary" onClick={() => update('salary', { min_tnd: null, max_tnd: null, period: 'month' })}><Plus size={16} /> Ajouter une fourchette</button>}
          <div className="save-row"><span>{saved && <><Check size={15} /> Modifications enregistrées</>}</span><button className="button-primary" type="submit" disabled={pending}>{pending ? 'Enregistrement…' : 'Enregistrer le brouillon'}<Check size={16} /></button></div>
        </form>
        <aside className="review-aside">
          {review ? <>
            <section className="insight-section salary-insight"><div className="insight-title"><span className="insight-icon coral"><BadgeCheck size={17} /></span><div><h2>Repère de rémunération</h2><span>DONNÉES DE MARCHÉ</span></div></div><p>{review.salary.message}</p>
              {review.salary.benchmark && <div className="benchmark"><div><strong>{review.salary.benchmark.median_tnd.toLocaleString('fr-TN')} <small>TND</small></strong><span>Médiane observée{review.salary.benchmark.period ? ` · ${review.salary.benchmark.period === 'month' ? 'par mois' : review.salary.benchmark.period === 'day' ? 'par jour' : 'par heure'}` : ''}</span></div><dl><div><dt>Source</dt><dd>{review.salary.benchmark.publisher}</dd></div><div><dt>Période</dt><dd>{review.salary.benchmark.period_start} — {review.salary.benchmark.period_end}</dd></div></dl>{review.salary.status !== 'matched' && <small className="benchmark-caveat">Repère fourni à titre indicatif; la période ou la fraîcheur ne permet pas une comparaison directe.</small>}</div>}
            </section>
            <section className="insight-section"><div className="insight-title"><span className="insight-icon amber"><Sparkles size={17} /></span><div><h2>À vérifier</h2><span>PISTES, PAS DES RÈGLES</span></div></div>{review.requirement_suggestions.filter((suggestion) => !dismissed.includes(suggestion.field)).length ? <ul className="suggestion-list">{review.requirement_suggestions.filter((suggestion) => !dismissed.includes(suggestion.field)).map((suggestion) => <li key={suggestion.field}><p>{suggestion.message}</p><div className="suggestion-actions"><button type="button" onClick={() => focusField(suggestion.field)}>Examiner le champ <ChevronRight size={14} /></button><button type="button" onClick={() => setDismissed([...dismissed, suggestion.field])}>Ignorer</button></div></li>)}</ul> : <p>Aucun autre point à vérifier. Ces pistes ne remplacent pas votre jugement.</p>}</section>
            <section className="insight-section candidate-insight"><div className="insight-title"><span className="insight-icon blue"><BriefcaseBusiness size={17} /></span><div><h2>Le profil recherché</h2><span>SELON VOTRE OFFRE</span></div></div><h3>{review.candidate_snapshot.title}</h3><p>{review.candidate_snapshot.responsibilities}</p><dl><div><dt>Expérience</dt><dd>{review.candidate_snapshot.experience_years_min ? `${review.candidate_snapshot.experience_years_min} ans minimum` : 'Non spécifiée'}</dd></div><div><dt>Lieu</dt><dd>{review.candidate_snapshot.location.delegation ? `${review.candidate_snapshot.location.delegation}, ` : ''}{review.candidate_snapshot.location.governorate_code}</dd></div><div><dt>Organisation</dt><dd>{workModeLabel(review.candidate_snapshot.work_mode)}</dd></div></dl><div className="snapshot-skills">{review.candidate_snapshot.skills.map((skill) => <span key={`${skill.label}-${skill.requirement}`} className={skill.requirement}>{skill.label}<i>{skill.requirement === 'required' ? 'Requis' : 'Souhaité'}</i></span>)}</div></section>
          </> : <div className="review-loading"><span className="loading-orbit" /><span>Préparation de la relecture…</span></div>}
          <div className="review-disclaimer"><CircleHelp size={15} /><p>Les repères ne remplacent pas votre jugement. Le brouillon n'est pas publié depuis cet espace.</p></div>
        </aside>
      </div>
    </section>
  );
}

function workModeLabel(mode: string) {
  return ({ on_site: 'Sur site', remote: 'À distance', hybrid: 'Hybride' } as Record<string, string>)[mode] ?? mode;
}