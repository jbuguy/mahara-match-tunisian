import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import {
  Bot, ChevronRight, Copy, FileText, Menu, MoreHorizontal,
  Mic, MicOff, Paperclip, Pause, Pencil, Plus, RefreshCcw,
  Search, Send, Square, Trash2, Volume2, X,
} from "lucide-react";
import {
  createCandidateAssistantSession,
  createEmployerPlanningSession,
  deleteCandidateAssistantSession,
  deleteEmployerPlanningSession,
  fetchCandidateAssistantSession,
  fetchCandidateAssistantSessions,
  fetchEmployerPlanningSessions,
  fetchEmployerPlanningMessages,
  renameCandidateAssistantSession,
  sendCandidateAssistantSessionMessage,
  sendEmployerPlanningMessage,
  addPlanningDocument,
  analyzePlanningSession,
  createPlanningDraftOffer,
  fetchPlanningDocuments,
  fetchPlanningRecommendations,
  updatePlanningRecommendation,
  type CandidateAssistantMessage,
  type CandidateAssistantSession,
  type CandidateAssistantSessionSummary,
  type EmployerPlanningSession,
  type PlanningMessage,
  type PlanningDocument,
  type PlanningRecommendation,
  type Role,
} from "./auth";

type SpeechRecognitionEventLike = Event & { results: ArrayLike<{ 0: { transcript: string } }> };
type SpeechRecognitionLike = {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  start: () => void;
  stop: () => void;
  abort: () => void;
  onresult: ((event: SpeechRecognitionEventLike) => void) | null;
  onerror: ((event: Event & { error: string }) => void) | null;
  onend: (() => void) | null;
};
type SpeechRecognitionConstructor = new () => SpeechRecognitionLike;

declare global {
  interface Window {
    SpeechRecognition?: SpeechRecognitionConstructor;
    webkitSpeechRecognition?: SpeechRecognitionConstructor;
  }
}

const projectTypes = {
  new_project: "Nouveau projet",
  department: "Nouveau département",
  expansion: "Expansion",
  organisational_need: "Besoin organisationnel",
  other: "Autre besoin",
} as const;

const prompts: Record<Role, string[]> = {
  candidate: ["Comment obtenir de meilleures correspondances ?", "Quelles compétences développer ?", "Préparer un entretien", "Explorer les métiers porteurs"],
  employer: ["Comment rédiger une offre claire ?", "Quels rôles recruter ?", "Planifier une nouvelle équipe", "Estimer les compétences nécessaires"],
  ministry_admin: ["Analyser les indicateurs de compétences", "Suivre les besoins territoriaux", "Préparer un rapport", "Comparer les secteurs"],
  training_provider: ["Adapter mon catalogue de formations", "Identifier les compétences demandées", "Suivre les inscrits", "Préparer une session"],
  operator: ["Diagnostiquer une anomalie", "Résumer l’activité de la plateforme", "Préparer une intervention", "Consulter les procédures"],
};

export function UnifiedAssistantWorkspace({
  token, role, projectId,
}: { token: string; role: Role; projectId?: string }) {
  const [sessions, setSessions] = useState<CandidateAssistantSessionSummary[]>([]);
  const [activeSession, setActiveSession] = useState<CandidateAssistantSession | null>(null);
  const [projects, setProjects] = useState<EmployerPlanningSession[]>([]);
  const [activeProject, setActiveProject] = useState<EmployerPlanningSession | null>(null);
  const [projectMessages, setProjectMessages] = useState<PlanningMessage[]>([]);
  const [text, setText] = useState("");
  const [search, setSearch] = useState("");
  const [searchOpen, setSearchOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const [railOpen, setRailOpen] = useState(false);
  const [panelOpen, setPanelOpen] = useState(() => localStorage.getItem("mahara-project-panel") !== "closed");
  const [panelTab, setPanelTab] = useState<"resume" | "context" | "recommendations">("resume");
  const [newProjectOpen, setNewProjectOpen] = useState(false);
  const [projectMenu, setProjectMenu] = useState<string | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (searchOpen) searchInputRef.current?.focus();
  }, [searchOpen]);

  const recognitionAvailable = Boolean(window.SpeechRecognition || window.webkitSpeechRecognition);
  const [voiceState, setVoiceState] = useState<"idle" | "listening" | "processing" | "error">("idle");
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError("");
      try {
        const history = await fetchCandidateAssistantSessions(token);
        let first = activeSession;
        const remembered = sessionStorage.getItem("mahara-assistant-session");
        const preferred = history.find((item) => item.id === remembered) ?? history[0];
        if (preferred) first = await fetchCandidateAssistantSession(token, preferred.id);
        else first = await createCandidateAssistantSession(token);
        if (!cancelled) {
          setSessions(history.some((item) => item.id === first?.id) ? history : [first as CandidateAssistantSession, ...history]);
          setActiveSession(first);
          if (first) sessionStorage.setItem("mahara-assistant-session", first.id);
        }
        if (role === "employer") {
          const rows = await fetchEmployerPlanningSessions(token);
          if (!cancelled) {
            setProjects(rows);
            setActiveProject(rows.find((item) => item.id === projectId) ?? null);
            const selectedProject = rows.find((item) => item.id === projectId);
            if (selectedProject) setProjectMessages(await fetchEmployerPlanningMessages(token, selectedProject.id));
          }
        }
      } catch (cause) {
        if (!cancelled) setError(cause instanceof Error ? cause.message : "Impossible de charger l’assistant.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void load();
    return () => { cancelled = true; recognitionRef.current?.abort(); };
  }, [token, role, projectId]);

  useEffect(() => {
    if (!activeProject && projectId && role === "employer") {
      window.location.hash = "#assistant";
    }
  }, [activeProject, projectId, role]);

  useEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;
    textarea.style.height = "0px";
    textarea.style.height = `${Math.min(textarea.scrollHeight, 120)}px`;
  }, [text]);

  async function sendMessage(content = text) {
    const message = content.trim();
    if (!message || sending || !activeSession) return;
    setText("");
    setSending(true);
    setError("");
    try {
      if (isProjectMode && activeProject) {
        setProjectMessages(await sendEmployerPlanningMessage(token, activeProject.id, message));
      } else {
        const updated = await sendCandidateAssistantSessionMessage(token, activeSession.id, message);
        setActiveSession(updated);
        setSessions((current) => [{ id: updated.id, title: updated.title, created_at: updated.created_at, updated_at: updated.updated_at }, ...current.filter((item) => item.id !== updated.id)]);
      }
      if ("speechSynthesis" in window) window.speechSynthesis.cancel();
    } catch (cause) {
      setText(message);
      setError(cause instanceof Error ? cause.message : "Votre message n’a pas pu être envoyé.");
    } finally {
      setSending(false);
    }
  }

  function startVoice() {
    const Constructor = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!Constructor) return;
    setVoiceState("listening");
    const recognition = new Constructor();
    recognition.lang = /^fr-/i.test(navigator.language) ? "fr-FR" : navigator.language || "fr-FR";
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.onresult = (event) => {
      const transcript = event.results[0]?.[0]?.transcript ?? "";
      setText((current) => `${current}${current ? " " : ""}${transcript}`);
      setVoiceState("processing");
    };
    recognition.onerror = () => setVoiceState("error");
    recognition.onend = () => setVoiceState((current) => current === "processing" ? "idle" : current);
    recognitionRef.current = recognition;
    recognition.start();
  }

  async function openSession(sessionId: string) {
    try {
      const opened = await fetchCandidateAssistantSession(token, sessionId);
      setActiveSession(opened);
      sessionStorage.setItem("mahara-assistant-session", sessionId);
      setRailOpen(false);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Impossible d’ouvrir la conversation."); }
  }

  async function newConversation() {
    try {
      const created = await createCandidateAssistantSession(token);
      setActiveSession(created);
      setSessions((current) => [created, ...current]);
      sessionStorage.setItem("mahara-assistant-session", created.id);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Impossible de créer la conversation."); }
  }

  async function renameConversation(session: CandidateAssistantSessionSummary) {
    const title = window.prompt("Nouveau titre", session.title);
    if (!title?.trim()) return;
    try {
      await renameCandidateAssistantSession(token, session.id, title.trim());
      setSessions((current) => current.map((item) => item.id === session.id ? { ...item, title: title.trim() } : item));
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Impossible de renommer la conversation."); }
  }

  async function removeConversation(sessionId: string) {
    if (!window.confirm("Supprimer cette conversation ?")) return;
    try {
      await deleteCandidateAssistantSession(token, sessionId);
      const remaining = sessions.filter((item) => item.id !== sessionId);
      setSessions(remaining);
      if (activeSession?.id === sessionId) {
        if (remaining[0]) await openSession(remaining[0].id);
        else await newConversation();
      }
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Impossible de supprimer la conversation."); }
  }

  async function removeProject(project: EmployerPlanningSession) {
    if (!window.confirm(`Supprimer « ${project.title} » et ses données ?`)) return;
    await deleteEmployerPlanningSession(token, project.id);
    setProjects((current) => current.filter((item) => item.id !== project.id));
    if (activeProject?.id === project.id) window.location.hash = "#assistant";
  }

  const visibleSessions = sessions.filter((item) => item.title.toLocaleLowerCase().includes(search.toLocaleLowerCase()));
  const isProjectMode = role === "employer" && Boolean(activeProject);

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    void sendMessage();
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void sendMessage();
    }
  }

  return <section className="unified-assistant">
    <button className="unified-assistant__mobile-menu icon-button" aria-label="Ouvrir les conversations" onClick={() => setRailOpen(true)}><Menu size={18}/></button>
    <aside className={`unified-assistant__rail ${railOpen ? "is-open" : ""}`} aria-label="Conversations et projets">
      <div className="assistant-rail__header">
        <button className="assistant-new-button" onClick={() => void newConversation()}><Plus size={17}/> Nouvelle conversation</button>
      </div>
      <div className={`assistant-search ${searchOpen ? "is-open" : ""}`}>
        <button type="button" className="icon-button assistant-search__toggle" aria-label={searchOpen ? "Fermer la recherche" : "Rechercher une conversation"} aria-expanded={searchOpen} onClick={() => setSearchOpen((current) => !current)}>
          {searchOpen ? <X size={18}/> : <Search size={18}/>}
        </button>
        {searchOpen && <input ref={searchInputRef} value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Rechercher une conversation"/>}
      </div>
      {role === "employer" && <>
        <div className="assistant-section__heading"><span>PROJETS</span><button className="icon-button" aria-label="Créer un projet" onClick={() => setNewProjectOpen(true)}><Plus size={16}/></button></div>
        <nav className="assistant-project-list" aria-label="Projets">
          {projects.filter((item) => item.status !== "archived").map((project) =>
            <button key={project.id} className={`assistant-project-row ${activeProject?.id === project.id ? "is-active" : ""}`} onClick={() => { window.location.hash = `#assistant/project/${project.id}`; setRailOpen(false); }}>
              <span className="status-dot"/><span><strong>{project.title}</strong><small>{project.status === "draft" ? "Brouillon" : project.status === "archived" ? "Archivé" : "En cours"}</small></span>
              {activeProject?.id === project.id && <span role="button" tabIndex={0} className="assistant-project-menu" aria-label="Menu du projet" onClick={(event) => { event.stopPropagation(); setProjectMenu(projectMenu === project.id ? null : project.id); }}><MoreHorizontal size={16}/></span>}
            </button>)}
          {projectMenu && <button className="assistant-project-delete" type="button" onClick={() => void removeProject(projects.find((item) => item.id === projectMenu)!)}><Trash2 size={14}/> Supprimer</button>}
        </nav>
      </>}
      <div className="assistant-section__heading"><span>CONVERSATIONS</span></div>
      <nav className="assistant-conversation-list" aria-label="Conversations">
        {visibleSessions.map((session) => <div className={`assistant-conversation-row ${activeSession?.id === session.id ? "is-active" : ""}`} key={session.id}>
          <button className="assistant-conversation-title" onClick={() => void openSession(session.id)}>{session.title}</button>
          <button className="icon-button" aria-label={`Options pour ${session.title}`} onClick={() => void renameConversation(session)}><Pencil size={14}/></button>
          <button className="icon-button" aria-label={`Supprimer ${session.title}`} onClick={() => void removeConversation(session.id)}><Trash2 size={14}/></button>
        </div>)}
      </nav>
    </aside>
    <main className="unified-assistant__chat">
      <header className="assistant-chat__header">
        <h1 className="sr-only">{role === "candidate" ? "Votre assistant carrière" : role === "employer" ? "Votre assistant recrutement" : "Votre assistant"}</h1>
        <div><strong>{isProjectMode ? activeProject?.title : activeSession?.title || "Assistant"}</strong>{isProjectMode && <><span className="assistant-project-type">{projectTypes[activeProject!.project_type]}</span><span className="status-badge">En cours</span></>}</div>
        {isProjectMode && <button className="button button--secondary button--small" onClick={() => { setPanelOpen((current) => { localStorage.setItem("mahara-project-panel", current ? "closed" : "open"); return !current; }); }}>Panneau du projet</button>}
      </header>
      <div className="assistant-chat__messages" aria-live="polite">
        {loading ? <div className="assistant-loading">Chargement de la conversation…</div> :
          (isProjectMode ? projectMessages : activeSession?.messages ?? []).length ? (isProjectMode ? projectMessages : activeSession?.messages ?? []).map((message, index) => <AssistantMessage key={`${message.role}-${index}`} message={message} />) :
          <div className="assistant-empty">
            <span className="assistant-empty__icon"><Bot size={28}/></span>
            <h2>{isProjectMode ? "Précisons votre projet" : role === "candidate" ? "Votre assistant carrière" : role === "employer" ? "Votre assistant recrutement" : "Parlons de votre avenir"}</h2>
            <div className="assistant-prompts">{prompts[role].map((prompt) => <button key={prompt} onClick={() => void sendMessage(prompt)}>{prompt}<ChevronRight size={16}/></button>)}</div>
          </div>}
        {sending && <p className="assistant-pending">L’assistant prépare sa réponse…</p>}
        {error && <p className="workspace-error" role="alert">{error}</p>}
      </div>
      <form className="assistant-composer-wrap" onSubmit={handleSubmit}>
        <div className="assistant-composer">
          {isProjectMode && <button type="button" className="icon-button" aria-label="Joindre un document" title="Joindre un document" disabled><Paperclip size={18}/></button>}
          <textarea ref={textareaRef} value={text} onChange={(event) => setText(event.target.value)} onKeyDown={handleKeyDown} rows={1} aria-label="Votre message" placeholder="Écrivez votre message…" maxLength={3000}/>
          <button type="button" className={`icon-button assistant-mic ${voiceState === "listening" ? "is-listening" : ""}`} aria-label={voiceState === "listening" ? "Arrêter l’écoute" : "Dicter un message"} title={recognitionAvailable ? "Dicter un message" : "Reconnaissance vocale non disponible"} disabled={!recognitionAvailable} onClick={() => voiceState === "listening" ? recognitionRef.current?.stop() : startVoice()}>
            {voiceState === "listening" ? <Square size={16}/> : recognitionAvailable ? <Mic size={18}/> : <MicOff size={18}/>}
          </button>
          <button type="submit" className="assistant-send" aria-label="Envoyer le message" disabled={sending || !text.trim()}><Send size={18}/></button>
        </div>
        <p>{voiceState === "listening" ? "Écoute en cours…" : voiceState === "error" ? "Échec de l’écoute. Réessayez." : "L’assistant peut se tromper. Vérifiez les informations importantes."}</p>
      </form>
    </main>
    {isProjectMode && activeProject && panelOpen && <ProjectPanel token={token} project={activeProject} activeTab={panelTab} onTabChange={setPanelTab} onClose={() => setPanelOpen(false)}/>}
    {newProjectOpen && <NewProjectDialog token={token} onClose={() => setNewProjectOpen(false)} onCreated={(project) => { setProjects((current) => [project, ...current]); setNewProjectOpen(false); window.location.hash = `#assistant/project/${project.id}`; }}/>}
  </section>;
}

function AssistantMessage({ message }: { message: CandidateAssistantMessage }) {
  const [speaking, setSpeaking] = useState(false);
  function speak() {
    if (!("speechSynthesis" in window)) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(message.content.replace(/[#*_]/g, ""));
    utterance.lang = /[\u0600-\u06FF]/.test(message.content) ? "ar-TN" : /^\s*[a-z]/i.test(message.content) && /\b(the|and|your|please)\b/i.test(message.content) ? "en-US" : "fr-FR";
    utterance.onend = () => setSpeaking(false);
    setSpeaking(true);
    window.speechSynthesis.speak(utterance);
  }
  if (message.role === "user") return <div className="assistant-user-message">{message.content}</div>;
  return <article className={`assistant-response ${speaking ? "is-speaking" : ""}`}>
    <span className="assistant-response__icon"><Bot size={16}/></span>
    <div><div className="assistant-response__text">{message.content}</div><div className="assistant-response__actions">
      <button className="icon-button" aria-label="Copier" title="Copier" onClick={() => void navigator.clipboard.writeText(message.content)}><Copy size={15}/></button>
      <button className="icon-button" aria-label="Lire à voix haute" title="Lire à voix haute" aria-pressed={speaking} onClick={speaking ? () => { window.speechSynthesis.cancel(); setSpeaking(false); } : speak}>{speaking ? <Pause size={15}/> : <Volume2 size={15}/>}</button>
      <button className="icon-button" aria-label="Régénérer" title="Régénérer" disabled><RefreshCcw size={15}/></button>
    </div></div>
  </article>;
}

function ProjectPanel({ token, project, activeTab, onTabChange, onClose }: {
  token: string; project: EmployerPlanningSession; activeTab: "resume" | "context" | "recommendations"; onTabChange: (tab: "resume" | "context" | "recommendations") => void; onClose: () => void;
}) {
  const summary = project.project_summary as Record<string, unknown>;
  const [documents, setDocuments] = useState<PlanningDocument[]>([]);
  const [recommendations, setRecommendations] = useState<PlanningRecommendation[]>([]);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    void Promise.all([fetchPlanningDocuments(token, project.id), fetchPlanningRecommendations(token, project.id)])
      .then(([loadedDocuments, loadedRecommendations]) => {
        setDocuments(loadedDocuments);
        setRecommendations(loadedRecommendations);
      })
      .catch(() => undefined);
  }, [project.id, token]);

  return <aside className="assistant-project-panel" aria-label="Panneau du projet">
    <header><strong>Projet</strong><button className="icon-button" aria-label="Fermer le panneau" onClick={onClose}><X size={17}/></button></header>
    <div className="assistant-project-tabs">
      <button className={activeTab === "resume" ? "is-active" : ""} onClick={() => onTabChange("resume")}>Résumé</button>
      <button className={activeTab === "context" ? "is-active" : ""} onClick={() => onTabChange("context")}>Contexte</button>
      <button className={activeTab === "recommendations" ? "is-active" : ""} onClick={() => onTabChange("recommendations")}>Recommandations</button>
    </div>
    <div className="assistant-project-panel__body">
      {activeTab === "resume" && Object.keys(summary).length ? Object.entries(summary).map(([key, value]) => <div className="summary-row" key={key}><span><strong>{key}</strong><small>{typeof value === "object" ? JSON.stringify(value) : String(value)}</small></span><span className="summary-tag">Fait confirmé</span></div>) : activeTab === "resume" ? <div className="assistant-panel-empty"><FileText size={22}/><h3>Résumé à construire</h3><p>Discutez avec l’assistant pour préciser les objectifs du projet.</p></div> : null}
      {activeTab === "context" && (documents.length ? <div className="assistant-document-list">{documents.map((document) => <div className="assistant-document" key={document.id}><FileText size={18}/><span><strong>{document.filename}</strong><small>{document.processing_status}</small></span></div>)}</div> : <div className="assistant-panel-empty"><FileText size={22}/><h3>Aucun contexte sélectionné</h3><p>Ajoutez un document textuel au projet pour l’intégrer à l’analyse.</p></div>)}
      {activeTab === "context" && <input className="assistant-document-input" type="file" accept=".txt,text/plain" aria-label="Ajouter un document" onChange={(event) => {
        const file = event.target.files?.[0];
        if (!file) return;
        void file.text().then((content) => addPlanningDocument(token, project.id, { filename: file.name, content_type: "text/plain", content }))
          .then((document) => setDocuments((current) => [...current, document]))
          .catch(() => undefined);
        event.target.value = "";
      }}/>}
      {activeTab === "recommendations" && <div className="assistant-recommendations">
        {recommendations.map((recommendation) => <article className="assistant-recommendation" key={recommendation.id}>
          <span className={`summary-tag summary-tag--${recommendation.status}`}>{recommendation.status === "approved" ? "Approuvée" : recommendation.status === "rejected" ? "Rejetée" : "Suggestion IA"}</span>
          <h3>{recommendation.title}</h3><p>{recommendation.rationale}</p><small>{recommendation.skills.join(" · ")}</small>
          <div className="assistant-recommendation__actions">
            <button className="button button--secondary button--small" disabled={busy} onClick={() => void updatePlanningRecommendation(token, project.id, recommendation.id, { status: "approved" }).then((updated) => setRecommendations((current) => current.map((item) => item.id === updated.id ? updated : item)))}>Approuver</button>
            {recommendation.recommendation_type === "hire" && <button className="button button--secondary button--small" disabled={busy || recommendation.status !== "approved"} onClick={async () => { setBusy(true); await createPlanningDraftOffer(token, project.id, recommendation.id); setBusy(false); }}>Créer un brouillon</button>}
          </div>
        </article>)}
        {!recommendations.length && <div className="assistant-panel-empty"><Bot size={22}/><h3>Aucune recommandation</h3><p>Lancez l’analyse à partir du résumé confirmé.</p></div>}
        <button className="button button--primary" disabled={busy} onClick={async () => { setBusy(true); try { setRecommendations(await analyzePlanningSession(token, project.id)); } finally { setBusy(false); } }}>{busy ? "Analyse…" : "Analyser le projet"}</button>
      </div>}
    </div>
  </aside>;
}

function NewProjectDialog({ token, onClose, onCreated }: { token: string; onClose: () => void; onCreated: (project: EmployerPlanningSession) => void }) {
  const [title, setTitle] = useState("");
  const [type, setType] = useState<EmployerPlanningSession["project_type"]>("other");
  const [description, setDescription] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (title.trim().length < 2) return;
    setBusy(true);
    try { onCreated(await createEmployerPlanningSession(token, { title: title.trim(), description: description.trim() || null, project_type: type })); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Impossible de créer le projet."); }
    finally { setBusy(false); }
  }
  return <div className="dialog-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
    <form className="assistant-project-dialog" role="dialog" aria-modal="true" aria-labelledby="new-project-title" onSubmit={submit}>
      <header><h2 id="new-project-title">Nouveau projet</h2><button type="button" className="icon-button" aria-label="Fermer" onClick={onClose}><X size={18}/></button></header>
      <label className="form-field"><span className="form-field__label">Nom du projet</span><input className="input" required minLength={2} maxLength={160} value={title} onChange={(event) => setTitle(event.target.value)}/></label>
      <label className="form-field"><span className="form-field__label">Type de besoin</span><select className="input" value={type} onChange={(event) => setType(event.target.value as EmployerPlanningSession["project_type"])}>{Object.entries(projectTypes).map(([value, label]) => <option value={value} key={value}>{label}</option>)}</select></label>
      <label className="form-field"><span className="form-field__label">Description facultative</span><textarea className="input" maxLength={2000} value={description} onChange={(event) => setDescription(event.target.value)}/></label>
      {error && <p role="alert" className="workspace-error">{error}</p>}
      <div className="assistant-dialog-actions"><button type="button" className="button button--secondary" onClick={onClose}>Annuler</button><button className="button button--primary" disabled={busy || title.trim().length < 2}>{busy ? "Création…" : "Créer le projet"}</button></div>
    </form>
  </div>;
}
