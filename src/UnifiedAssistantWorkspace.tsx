import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import {
  Archive, Bot, Check, ChevronRight, Copy, Download, FileText, Menu, MoreHorizontal,
  Mic, MicOff, Paperclip, Pause, Pencil, Plus, RefreshCcw,
  Search, Send, Square, Trash2, Volume2, X,
} from "lucide-react";
import {
  createCandidateRoadmapProject,
  createCandidateLearningProject,
  createCandidateLearningMilestone,
  deleteCandidateLearningDocument,
  downloadCandidateLearningDocument,
  decideCandidateRoadmapProposal,
  enrollInCourse,
  fetchCandidateEnrollments,
  fetchCandidateMatches,
  fetchCandidateRoadmap,
  fetchCandidateRoadmapAssessments,
  fetchCandidateRoadmapProjects,
  fetchCandidateRoadmapProposals,
  fetchPublishedCourses,
  createCandidateAssistantSession,
  createEmployerPlanningSession,
  deleteCandidateAssistantSession,
  deleteEmployerPlanningSession,
  fetchCandidateAssistantSession,
  fetchCandidateAssistantSessions,
  fetchCandidateLearningProjects,
  fetchCandidateLearningMilestones,
  fetchCandidateLearningDocuments,
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
  updateCandidateRoadmapGoal,
  updateCandidateRoadmapStep,
  updateCandidateRoadmapProjectStatus,
  toggleCandidateLearningProjectArchive,
  updateCandidateLearningMilestoneStatus,
  uploadCandidateLearningDocument,
  type CandidateAssistantMessage,
  type CandidateAssistantSession,
  type CandidateAssistantSessionSummary,
  type CandidateLearningProject,
  type CandidateLearningMilestone,
  type CandidateLearningDocument,
  type CandidateRoadmap,
  type CandidateRoadmapAssessment,
  type CandidateRoadmapGoalUpdate,
  type CandidateRoadmapProject,
  type CandidateRoadmapProposal,
  type CourseEnrollment,
  type JobMatch,
  type TrainingCourse,
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
  token, role, projectId, onNavigate,
}: { token: string; role: Role; projectId?: string; onNavigate?: (page: string) => void }) {
  const [sessions, setSessions] = useState<CandidateAssistantSessionSummary[]>([]);
  const [activeSession, setActiveSession] = useState<CandidateAssistantSession | null>(null);
  const [learningProjects, setLearningProjects] = useState<CandidateLearningProject[]>([]);
  const [activeLearningProject, setActiveLearningProject] = useState<CandidateLearningProject | null>(null);
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
  const [roadmapOpen, setRoadmapOpen] = useState(false);
  const [learningRoadmapOpen, setLearningRoadmapOpen] = useState(false);
  const [panelTab, setPanelTab] = useState<"resume" | "context" | "recommendations">("resume");
  const [newProjectOpen, setNewProjectOpen] = useState(false);
  const [newLearningProjectOpen, setNewLearningProjectOpen] = useState(false);
  const [showArchivedLearningProjects, setShowArchivedLearningProjects] = useState(false);
  const [projectMenu, setProjectMenu] = useState<string | null>(null);
  const [editingConversationId, setEditingConversationId] = useState<string | null>(null);
  const [conversationTitleDraft, setConversationTitleDraft] = useState("");
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
        if (role === "candidate") {
          try {
            const learningProjectRows = await fetchCandidateLearningProjects(token, true);
            if (!cancelled) setLearningProjects(learningProjectRows);
          } catch {
            // The general assistant remains usable if the optional project list is unavailable.
          }
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
      const created = await createCandidateAssistantSession(token, activeLearningProject?.id);
      setActiveSession(created);
      setSessions((current) => [created, ...current]);
      sessionStorage.setItem("mahara-assistant-session", created.id);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Impossible de créer la conversation."); }
  }

  async function openLearningProject(project: CandidateLearningProject | null) {
    setError("");
    setLoading(true);
    try {
      const history = await fetchCandidateAssistantSessions(token, project?.id);
      if (!history.length && project?.status === "archived") {
        throw new Error("Ce projet archivé n’a pas encore de conversation. Restaurez-le pour démarrer une conversation.");
      }
      const session = history[0]
        ? await fetchCandidateAssistantSession(token, history[0].id)
        : await createCandidateAssistantSession(token, project?.id);
      setActiveLearningProject(project);
      setSessions(history.length ? history : [session]);
      setActiveSession(session);
      sessionStorage.setItem("mahara-assistant-session", session.id);
      setRailOpen(false);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Impossible d’ouvrir ce projet.");
    } finally {
      setLoading(false);
    }
  }

  async function archiveLearningProject(project: CandidateLearningProject) {
    try {
      const updated = await toggleCandidateLearningProjectArchive(token, project.id);
      setLearningProjects((current) => current.map((item) => item.id === updated.id ? updated : item));
      if (activeLearningProject?.id === updated.id && updated.status === "archived") {
        setLearningRoadmapOpen(false);
        await openLearningProject(null);
      }
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Impossible de mettre à jour le projet.");
    }
  }

  async function createLearningProject(input: Pick<CandidateLearningProject, "title" | "objective" | "target_profession" | "starting_level">) {
    const created = await createCandidateLearningProject(token, input);
    setLearningProjects((current) => [created, ...current]);
    setNewLearningProjectOpen(false);
    await openLearningProject(created);
  }

  function startRenamingConversation(session: CandidateAssistantSessionSummary) {
    setEditingConversationId(session.id);
    setConversationTitleDraft(session.title);
  }

  async function renameConversation(session: CandidateAssistantSessionSummary) {
    const title = conversationTitleDraft.trim();
    if (!title) return;
    try {
      await renameCandidateAssistantSession(token, session.id, title.trim());
      setSessions((current) => current.map((item) => item.id === session.id ? { ...item, title: title.trim() } : item));
      setEditingConversationId(null);
      setConversationTitleDraft("");
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Impossible de renommer la conversation."); }
  }

  function cancelRenamingConversation() {
    setEditingConversationId(null);
    setConversationTitleDraft("");
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
      {role === "candidate" && <>
        <div className="assistant-section__heading">
          <span>MES PROJETS D’APPRENTISSAGE</span>
          <button className="icon-button" aria-label="Créer un projet d’apprentissage" onClick={() => setNewLearningProjectOpen(true)}><Plus size={16}/></button>
        </div>
        <nav className="assistant-project-list assistant-learning-projects" aria-label="Projets d’apprentissage">
          <button className={`assistant-project-row ${activeLearningProject === null ? "is-active" : ""}`} onClick={() => void openLearningProject(null)}>
            <span className="status-dot"/><span><strong>Assistant général</strong><small>Conversation hors projet</small></span>
          </button>
          {learningProjects.filter((project) => showArchivedLearningProjects || project.status === "active").map((project) =>
            <div className="learning-project-list-row" key={project.id}>
              <button className={`assistant-project-row ${activeLearningProject?.id === project.id ? "is-active" : ""}`} onClick={() => void openLearningProject(project)}>
                <span className="status-dot"/><span><strong>{project.title}</strong><small>{project.status === "archived" ? "Archivé" : project.target_profession || "Projet d’apprentissage"}</small></span>
              </button>
              <button className="icon-button learning-project-archive" aria-label={`${project.status === "archived" ? "Restaurer" : "Archiver"} ${project.title}`} title={project.status === "archived" ? "Restaurer" : "Archiver"} onClick={() => void archiveLearningProject(project)}><Archive size={14}/></button>
            </div>)}
          {learningProjects.some((project) => project.status === "archived") && <button className="assistant-learning-archive-toggle" onClick={() => setShowArchivedLearningProjects((current) => !current)}>{showArchivedLearningProjects ? "Masquer les archives" : "Afficher les projets archivés"}</button>}
          {!learningProjects.length && <p className="assistant-learning-empty">Créez un projet pour garder son objectif et ses conversations ensemble.</p>}
        </nav>
      </>}
      <div className="assistant-section__heading"><span>CONVERSATIONS</span></div>
      <nav className="assistant-conversation-list" aria-label="Conversations">
        {visibleSessions.map((session) => <div className={`assistant-conversation-row ${activeSession?.id === session.id ? "is-active" : ""}`} key={session.id}>
          {editingConversationId === session.id ? <>
            <input
              className="assistant-conversation-title-input"
              aria-label={`Renommer ${session.title}`}
              value={conversationTitleDraft}
              onChange={(event) => setConversationTitleDraft(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter") void renameConversation(session);
                if (event.key === "Escape") cancelRenamingConversation();
              }}
              autoFocus
            />
            <button className="icon-button assistant-conversation-confirm" aria-label="Valider le nouveau titre" disabled={!conversationTitleDraft.trim()} onClick={() => void renameConversation(session)}><Check size={14}/></button>
            <button className="icon-button" aria-label="Annuler le renommage" onClick={cancelRenamingConversation}><X size={14}/></button>
          </> : <>
            <button
              className="assistant-conversation-title"
              title={session.title}
              onClick={() => void openSession(session.id)}
            >
              {session.title}
            </button>
            <button className="icon-button" aria-label={`Renommer ${session.title}`} onClick={() => startRenamingConversation(session)}><Pencil size={14}/></button>
            <button className="icon-button" aria-label={`Supprimer ${session.title}`} onClick={() => void removeConversation(session.id)}><Trash2 size={14}/></button>
          </>}
        </div>)}
      </nav>
    </aside>
    <main className="unified-assistant__chat">
      <header className="assistant-chat__header">
        <h1 className="sr-only">{role === "candidate" ? "Votre assistant carrière" : role === "employer" ? "Votre assistant recrutement" : "Votre assistant"}</h1>
        <div><strong>{isProjectMode ? activeProject?.title : activeLearningProject?.title || activeSession?.title || "Assistant"}</strong>{isProjectMode && <><span className="assistant-project-type">{projectTypes[activeProject!.project_type]}</span><span className="status-badge">En cours</span></>}{activeLearningProject && <><span className="assistant-project-type">{activeLearningProject.target_profession || "Projet d’apprentissage"}</span><span className="status-badge">{activeLearningProject.status === "active" ? "Actif" : "Archivé"}</span></>}</div>
        {role === "candidate" && <button className="button button--secondary button--small" aria-expanded={roadmapOpen} onClick={() => { setLearningRoadmapOpen(false); setRoadmapOpen((current) => !current); }}>Mon parcours</button>}
        {activeLearningProject && <button className="button button--secondary button--small" aria-expanded={learningRoadmapOpen} onClick={() => { setRoadmapOpen(false); setLearningRoadmapOpen((current) => !current); }}>Roadmap du projet</button>}
        {isProjectMode && <button className="button button--secondary button--small" onClick={() => { setPanelOpen((current) => { localStorage.setItem("mahara-project-panel", current ? "closed" : "open"); return !current; }); }}>Panneau du projet</button>}
      </header>
      <div className="assistant-chat__messages" aria-live="polite">
        {loading ? <div className="assistant-loading">Chargement de la conversation…</div> :
          (isProjectMode ? projectMessages : activeSession?.messages ?? []).length ? (isProjectMode ? projectMessages : activeSession?.messages ?? []).map((message, index) => <AssistantMessage key={`${message.role}-${index}`} message={message} />) :
          <div className="assistant-empty">
            <span className="assistant-empty__icon"><Bot size={28}/></span>
            <h2>{isProjectMode || activeLearningProject ? "Reprenons votre objectif" : role === "candidate" ? "Votre assistant carrière" : role === "employer" ? "Votre assistant recrutement" : "Parlons de votre avenir"}</h2>
            {activeLearningProject && <p className="assistant-learning-objective">{activeLearningProject.objective}</p>}
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
    {role === "candidate" && roadmapOpen && <RoadmapPanel token={token} onClose={() => setRoadmapOpen(false)} onNavigate={onNavigate}/>}
    {role === "candidate" && activeLearningProject && learningRoadmapOpen && <LearningProjectRoadmapPanel token={token} project={activeLearningProject} onClose={() => setLearningRoadmapOpen(false)}/>}
    {newLearningProjectOpen && <LearningProjectDialog onClose={() => setNewLearningProjectOpen(false)} onCreated={createLearningProject}/>}
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

function LearningProjectDialog({
  onClose,
  onCreated,
}: {
  onClose: () => void;
  onCreated: (project: Pick<CandidateLearningProject, "title" | "objective" | "target_profession" | "starting_level">) => Promise<void>;
}) {
  const [title, setTitle] = useState("");
  const [objective, setObjective] = useState("");
  const [targetProfession, setTargetProfession] = useState("");
  const [startingLevel, setStartingLevel] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await onCreated({
        title: title.trim(),
        objective: objective.trim(),
        target_profession: targetProfession.trim() || null,
        starting_level: startingLevel.trim() || null,
      });
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Impossible de créer le projet.");
    } finally {
      setBusy(false);
    }
  }

  return <div className="dialog-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
    <form className="assistant-project-dialog" role="dialog" aria-modal="true" aria-labelledby="new-learning-project-title" onSubmit={(event) => void submit(event)}>
      <header><h2 id="new-learning-project-title">Nouveau projet d’apprentissage</h2><button type="button" className="icon-button" aria-label="Fermer" onClick={onClose}><X size={18}/></button></header>
      <p>Créez un espace pour votre objectif. Vos conversations restent séparées entre les projets.</p>
      <label className="form-field"><span className="form-field__label">Nom du projet</span><input className="input" required minLength={2} maxLength={160} value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Ex. Devenir développeuse backend"/></label>
      <label className="form-field"><span className="form-field__label">Objectif d’apprentissage</span><textarea className="input" required minLength={2} maxLength={2000} value={objective} onChange={(event) => setObjective(event.target.value)} placeholder="Que souhaitez-vous apprendre ou être capable de réaliser ?"/></label>
      <label className="form-field"><span className="form-field__label">Métier visé (facultatif)</span><input className="input" maxLength={160} value={targetProfession} onChange={(event) => setTargetProfession(event.target.value)}/></label>
      <label className="form-field"><span className="form-field__label">Votre niveau de départ (facultatif)</span><input className="input" maxLength={60} value={startingLevel} onChange={(event) => setStartingLevel(event.target.value)} placeholder="Ex. Débutant, notions de Python"/></label>
      {error && <p role="alert" className="workspace-error">{error}</p>}
      <div className="assistant-dialog-actions"><button type="button" className="button button--secondary" onClick={onClose}>Annuler</button><button className="button button--primary" disabled={busy || title.trim().length < 2 || objective.trim().length < 2}>{busy ? "Création…" : "Créer le projet"}</button></div>
    </form>
  </div>;
}

function LearningProjectRoadmapPanel({
  token,
  project,
  onClose,
}: {
  token: string;
  project: CandidateLearningProject;
  onClose: () => void;
}) {
  const [milestones, setMilestones] = useState<CandidateLearningMilestone[]>([]);
  const [documents, setDocuments] = useState<CandidateLearningDocument[]>([]);
  const [courses, setCourses] = useState<TrainingCourse[]>([]);
  const [enrollments, setEnrollments] = useState<CourseEnrollment[]>([]);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [skill, setSkill] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [documentError, setDocumentError] = useState("");
  const [courseError, setCourseError] = useState("");
  const [enrollingCourseId, setEnrollingCourseId] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    void Promise.allSettled([
      fetchCandidateLearningMilestones(token, project.id),
      fetchCandidateLearningDocuments(token, project.id),
      fetchPublishedCourses(token),
      fetchCandidateEnrollments(token),
    ]).then(([milestoneResult, documentResult, courseResult, enrollmentResult]) => {
      if (cancelled) return;
      if (milestoneResult.status === "fulfilled") setMilestones(milestoneResult.value);
      else setError(milestoneResult.reason instanceof Error ? milestoneResult.reason.message : "Impossible de charger la roadmap du projet.");
      if (documentResult.status === "fulfilled") setDocuments(documentResult.value);
      else setDocumentError(documentResult.reason instanceof Error ? documentResult.reason.message : "Impossible de charger les documents.");
      if (courseResult.status === "fulfilled") setCourses(courseResult.value);
      else setCourseError(courseResult.reason instanceof Error ? courseResult.reason.message : "Impossible de charger les formations.");
      if (enrollmentResult.status === "fulfilled") setEnrollments(enrollmentResult.value);
      else setCourseError(enrollmentResult.reason instanceof Error ? enrollmentResult.reason.message : "Impossible de charger vos inscriptions.");
    }).finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [token, project.id]);

  async function addMilestone(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const created = await createCandidateLearningMilestone(token, project.id, {
        title: title.trim(),
        description: description.trim(),
        skill: skill.trim() || null,
      });
      setMilestones((current) => [...current, created]);
      setTitle("");
      setDescription("");
      setSkill("");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Impossible d’ajouter cette étape.");
    } finally {
      setBusy(false);
    }
  }

  async function changeStatus(milestone: CandidateLearningMilestone, status: CandidateLearningMilestone["status"]) {
    setBusy(true);
    setError("");
    try {
      const updated = await updateCandidateLearningMilestoneStatus(token, project.id, milestone.id, status);
      setMilestones((current) => current.map((item) => item.id === updated.id ? updated : item));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Impossible de mettre à jour cette étape.");
    } finally {
      setBusy(false);
    }
  }

  async function enrollInRecommendedCourse(courseId: string) {
    setEnrollingCourseId(courseId);
    setCourseError("");
    try {
      const enrollment = await enrollInCourse(token, courseId);
      setEnrollments((current) => [...current.filter((item) => item.course_id !== courseId), enrollment]);
    } catch (cause) {
      setCourseError(cause instanceof Error ? cause.message : "Impossible de s’inscrire à cette formation.");
    } finally {
      setEnrollingCourseId(null);
    }
  }

  async function uploadDocument(file?: File) {
    if (!file) return;
    setUploading(true);
    setDocumentError("");
    try {
      const created = await uploadCandidateLearningDocument(token, project.id, file);
      setDocuments((current) => [created, ...current]);
    } catch (cause) {
      setDocumentError(cause instanceof Error ? cause.message : "Impossible d’ajouter ce document.");
    } finally {
      setUploading(false);
    }
  }

  async function downloadDocument(file: CandidateLearningDocument) {
    try {
      const blob = await downloadCandidateLearningDocument(token, project.id, file.id);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = file.filename;
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (cause) {
      setDocumentError(cause instanceof Error ? cause.message : "Impossible de télécharger ce document.");
    }
  }

  async function removeDocument(file: CandidateLearningDocument) {
    if (!window.confirm(`Supprimer « ${file.filename} » de ce projet ?`)) return;
    try {
      await deleteCandidateLearningDocument(token, project.id, file.id);
      setDocuments((current) => current.filter((item) => item.id !== file.id));
    } catch (cause) {
      setDocumentError(cause instanceof Error ? cause.message : "Impossible de supprimer ce document.");
    }
  }

  const completed = milestones.filter((milestone) => milestone.status === "completed").length;
  const progress = milestones.length ? Math.round(completed * 100 / milestones.length) : 0;
  const projectSkills = new Set(milestones.map((milestone) => milestone.skill?.trim().toLocaleLowerCase()).filter((value): value is string => Boolean(value)));
  const recommendedCourses = courses.map((course) => ({
    course,
    matchedSkills: course.skills.filter((courseSkill) => projectSkills.has(courseSkill.trim().toLocaleLowerCase())),
  })).filter(({ matchedSkills }) => matchedSkills.length > 0);

  return <aside className="assistant-roadmap-panel assistant-learning-roadmap-panel" aria-label={`Roadmap de ${project.title}`}>
    <header><div><strong>{project.title}</strong><small>Roadmap · {progress}% terminée</small></div><button className="icon-button" aria-label="Fermer la roadmap" onClick={onClose}><X size={17}/></button></header>
    <div className="assistant-roadmap-panel__body">
      <section className="assistant-learning-project-summary"><span>OBJECTIF</span><p>{project.objective}</p>{project.starting_level && <small>Niveau de départ : {project.starting_level}</small>}</section>
      <section className="assistant-roadmap-section assistant-learning-documents">
        <h3>Fichiers du projet</h3>
        <label className="assistant-learning-upload"><span>{uploading ? "Analyse du document…" : "Ajouter un PDF, DOCX, TXT ou Markdown (10 Mo max)"}</span><input type="file" accept=".pdf,.docx,.txt,.md,application/pdf,text/plain,text/markdown,application/vnd.openxmlformats-officedocument.wordprocessingml.document" disabled={uploading || project.status !== "active"} onChange={(event) => { void uploadDocument(event.target.files?.[0]); event.target.value = ""; }}/></label>
        {documents.map((file) => <article className="assistant-learning-document" key={file.id}>
          <span><strong>{file.filename}</strong><small>{file.processing_status === "completed" ? `${Math.ceil(file.size_bytes / 1024)} Ko · Texte disponible pour l’assistant` : file.error_message || "Le texte n’a pas pu être extrait."}</small></span>
          <button type="button" className="icon-button" aria-label={`Télécharger ${file.filename}`} onClick={() => void downloadDocument(file)}><Download size={15}/></button>
          <button type="button" className="icon-button" aria-label={`Supprimer ${file.filename}`} onClick={() => void removeDocument(file)}><Trash2 size={15}/></button>
        </article>)}
        {!documents.length && !loading && <p className="assistant-roadmap-note">Aucun document ajouté.</p>}
        {documentError && <p className="workspace-error" role="alert">{documentError}</p>}
      </section>
      <section className="assistant-roadmap-section">
        <h3>Étapes d’apprentissage</h3>
        {loading ? <p role="status">Chargement des étapes…</p> : milestones.length ? milestones.map((milestone, index) => <article className="assistant-roadmap-step" key={milestone.id}>
          <div><strong>{index + 1}. {milestone.title}</strong><small>{milestone.skill ? `${milestone.skill} · ` : ""}{milestone.description}</small></div>
          <select className="input" aria-label={`État de ${milestone.title}`} value={milestone.status} disabled={busy} onChange={(event) => void changeStatus(milestone, event.target.value as CandidateLearningMilestone["status"])}>
            <option value="planned">À commencer</option><option value="in_progress">En cours</option><option value="completed">Terminée</option>
          </select>
        </article>) : <p className="assistant-roadmap-note">Ajoutez des étapes pour organiser votre apprentissage.</p>}
      </section>
      <section className="assistant-roadmap-section assistant-learning-formations">
        <h3>Formations liées à votre projet</h3>
        {!projectSkills.size ? <p className="assistant-roadmap-note">Ajoutez une compétence à une étape pour trouver des formations correspondantes.</p> : recommendedCourses.length ? recommendedCourses.map(({ course, matchedSkills }) => {
          const enrollment = enrollments.find((item) => item.course_id === course.id);
          const full = course.enrollment_count >= course.capacity;
          return <article className="assistant-roadmap-step" key={course.id}>
            <div><strong>{course.title}</strong><small>{matchedSkills.join(" · ")} · {course.duration_hours} h{course.location ? ` · ${course.location}` : " · En ligne"}</small></div>
            {enrollment ? <span className="assistant-learning-enrollment">{enrollment.status === "completed" ? "Terminée" : enrollment.status === "withdrawn" ? "Désinscrit·e" : "Inscrit·e"}</span> : <button type="button" className="button button--secondary" disabled={Boolean(enrollingCourseId) || full || project.status !== "active"} onClick={() => void enrollInRecommendedCourse(course.id)}>{enrollingCourseId === course.id ? "Inscription…" : full ? "Complète" : "S’inscrire"}</button>}
          </article>;
        }) : <p className="assistant-roadmap-note">Aucune formation publiée ne correspond aux compétences de vos étapes.</p>}
        {courseError && <p className="workspace-error" role="alert">{courseError}</p>}
        <p className="assistant-roadmap-note">Les formations affichées proviennent du catalogue publié. Leur inscription reste distincte de la progression des étapes.</p>
      </section>
      <form className="assistant-roadmap-goal" onSubmit={(event) => void addMilestone(event)}>
        <h3>Ajouter une étape</h3>
        <label><span>Étape ou résultat attendu</span><input className="input" required minLength={2} maxLength={160} value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Ex. Créer une API REST"/></label>
        <label><span>Description</span><textarea className="input" required minLength={2} maxLength={2000} value={description} onChange={(event) => setDescription(event.target.value)}/></label>
        <label><span>Compétence concernée (facultatif)</span><input className="input" maxLength={100} value={skill} onChange={(event) => setSkill(event.target.value)}/></label>
        <button className="button button--primary" disabled={busy || loading}>{busy ? "Enregistrement…" : "Ajouter à la roadmap"}</button>
      </form>
      {error && <p className="workspace-error" role="alert">{error}</p>}
      <p className="assistant-roadmap-note">La progression suit les étapes que vous marquez. Elle ne constitue pas une validation de maîtrise.</p>
    </div>
  </aside>;
}

function RoadmapPanel({ token, onClose, onNavigate }: { token: string; onClose: () => void; onNavigate?: (page: string) => void }) {
  const [roadmap, setRoadmap] = useState<CandidateRoadmap | null>(null);
  const [matches, setMatches] = useState<JobMatch[]>([]);
  const [courses, setCourses] = useState<TrainingCourse[]>([]);
  const [enrollments, setEnrollments] = useState<CourseEnrollment[]>([]);
  const [projects, setProjects] = useState<CandidateRoadmapProject[]>([]);
  const [assessments, setAssessments] = useState<CandidateRoadmapAssessment[]>([]);
  const [proposals, setProposals] = useState<CandidateRoadmapProposal[]>([]);
  const [projectSkill, setProjectSkill] = useState("");
  const [projectTitle, setProjectTitle] = useState("");
  const [projectDescription, setProjectDescription] = useState("");
  const [goalType, setGoalType] = useState<CandidateRoadmapGoalUpdate["goal_type"]>("target_job");
  const [targetOfferId, setTargetOfferId] = useState("");
  const [goalTitle, setGoalTitle] = useState("");
  const [skillText, setSkillText] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  useEffect(() => {
    let cancelled = false;
    const requests = [
      fetchCandidateRoadmap(token),
      fetchCandidateMatches(token),
      fetchPublishedCourses(token),
      fetchCandidateEnrollments(token),
      fetchCandidateRoadmapProjects(token),
      fetchCandidateRoadmapAssessments(token),
      fetchCandidateRoadmapProposals(token),
    ] as const;
    void Promise.allSettled(requests)
      .then(([roadmapResult, matchesResult, coursesResult, enrollmentsResult, projectsResult, assessmentsResult, proposalsResult]) => {
        if (cancelled) return;
        if (roadmapResult.status === "rejected") {
          setError(roadmapResult.reason instanceof Error ? roadmapResult.reason.message : "Impossible de charger le parcours.");
          return;
        }
        const currentRoadmap = roadmapResult.value;
        const currentMatches = matchesResult.status === "fulfilled" ? matchesResult.value : [];
        setRoadmap(currentRoadmap);
        setMatches(currentMatches);
        setCourses(coursesResult.status === "fulfilled" ? coursesResult.value : []);
        setEnrollments(enrollmentsResult.status === "fulfilled" ? enrollmentsResult.value : []);
        setProjects(projectsResult.status === "fulfilled" ? projectsResult.value : []);
        setAssessments(assessmentsResult.status === "fulfilled" ? assessmentsResult.value : []);
        setProposals(proposalsResult.status === "fulfilled" ? proposalsResult.value : []);
        if (currentRoadmap.goal_type) setGoalType(currentRoadmap.goal_type);
        setTargetOfferId(currentRoadmap.target_offer_id ?? currentMatches[0]?.id ?? "");
        setGoalTitle(currentRoadmap.goal_title ?? currentMatches[0]?.title ?? "");
        setSkillText((currentRoadmap.selected_skills ?? []).join(", "));
        if ([matchesResult, coursesResult, enrollmentsResult, projectsResult, assessmentsResult, proposalsResult].some((result) => result.status === "rejected")) {
          setNotice("Une partie des recommandations ou du suivi est momentanément indisponible. Votre parcours reste accessible.");
        }
      })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [token]);

  async function saveGoal(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    const goal: CandidateRoadmapGoalUpdate = goalType === "target_job"
      ? { goal_type: goalType, title: goalTitle.trim(), target_offer_id: targetOfferId, skills: [] }
      : { goal_type: goalType, title: goalTitle.trim(), skills: skillText.split(",").map((skill) => skill.trim()).filter(Boolean) };
    try { setRoadmap(await updateCandidateRoadmapGoal(token, goal)); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Impossible d’enregistrer cet objectif."); }
    finally { setBusy(false); }
  }

  async function toggleStep(skill: string, completed: boolean) {
    setBusy(true);
    setError("");
    try { setRoadmap(await updateCandidateRoadmapStep(token, skill, completed)); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Impossible d’enregistrer la progression."); }
    finally { setBusy(false); }
  }

  async function enroll(courseId: string) {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const enrollment = await enrollInCourse(token, courseId);
      setEnrollments((current) => [...current.filter((item) => item.id !== enrollment.id), enrollment]);
      setNotice("Inscription ajoutée à vos formations.");
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Impossible de s’inscrire."); }
    finally { setBusy(false); }
  }

  async function addProject(event: FormEvent) {
    event.preventDefault();
    if (!projectSkill || projectTitle.trim().length < 2) return;
    setBusy(true);
    setError("");
    try {
      const project = await createCandidateRoadmapProject(token, { skill: projectSkill, title: projectTitle.trim(), description: projectDescription.trim() });
      setProjects((current) => [project, ...current]);
      setProjectSkill("");
      setProjectTitle("");
      setProjectDescription("");
      setNotice("Projet pratique ajouté au parcours.");
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Impossible d’ajouter le projet."); }
    finally { setBusy(false); }
  }

  async function changeProjectStatus(project: CandidateRoadmapProject, nextStatus: CandidateRoadmapProject["status"]) {
    setBusy(true);
    try {
      const updated = await updateCandidateRoadmapProjectStatus(token, project.id, nextStatus);
      setProjects((current) => current.map((item) => item.id === updated.id ? updated : item));
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Impossible de mettre à jour le projet."); }
    finally { setBusy(false); }
  }

  async function decideProposal(proposal: CandidateRoadmapProposal, decision: "accepted" | "rejected") {
    setBusy(true);
    setError("");
    try {
      await decideCandidateRoadmapProposal(token, proposal.id, decision);
      setProposals((current) => current.filter((item) => item.id !== proposal.id));
      if (decision === "accepted") setRoadmap(await fetchCandidateRoadmap(token));
      setNotice(decision === "accepted" ? "Proposition appliquée au parcours." : "Proposition rejetée.");
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Impossible de traiter la proposition."); }
    finally { setBusy(false); }
  }

  const missingKeys = new Set((roadmap?.steps ?? []).filter((step) => !step.completed).map((step) => step.skill_key));
  const recommendedCourses = courses.filter((course) => course.skills.some((skill) => missingKeys.has(skill.trim().toLocaleLowerCase()))).slice(0, 5);

  return <aside className="assistant-roadmap-panel" aria-label="Mon parcours professionnel">
    <header><div><strong>Mon parcours</strong><small>{roadmap?.progress_percent ?? 0}% de progression</small></div><button className="icon-button" aria-label="Fermer le parcours" onClick={onClose}><X size={17}/></button></header>
    <div className="assistant-roadmap-panel__body">
      {loading ? <p role="status">Chargement du parcours…</p> : <>
        <form className="assistant-roadmap-goal" onSubmit={(event) => void saveGoal(event)}>
          <h3>Votre objectif</h3>
          <label><span>Type d’objectif</span><select className="input" value={goalType} onChange={(event) => setGoalType(event.target.value as CandidateRoadmapGoalUpdate["goal_type"])}><option value="target_job">Un emploi publié</option><option value="skill_exploration">Explorer des compétences</option></select></label>
          {goalType === "target_job" ? <>
            <label><span>Emploi cible</span><select className="input" required value={targetOfferId} onChange={(event) => { setTargetOfferId(event.target.value); setGoalTitle(matches.find((match) => match.id === event.target.value)?.title ?? ""); }}><option value="">Choisir une offre publiée</option>{matches.map((match) => <option key={match.id} value={match.id}>{match.title} · {match.location}</option>)}</select></label>
            {!matches.length && <p className="assistant-roadmap-note">Aucune offre publiée n’est disponible pour le moment.</p>}
          </> : <>
            <label><span>Compétences à travailler (séparées par des virgules)</span><input className="input" required value={skillText} onChange={(event) => setSkillText(event.target.value)} placeholder="Python, SQL, communication"/></label>
            <label><span>Nom du parcours</span><input className="input" required minLength={2} maxLength={160} value={goalTitle} onChange={(event) => setGoalTitle(event.target.value)} placeholder="Ex. Renforcer mes compétences data"/></label>
          </>}
          <button className="button button--primary" disabled={busy || loading || (goalType === "target_job" && !targetOfferId)}>{busy ? "Enregistrement…" : "Mettre à jour le parcours"}</button>
        </form>
        {roadmap?.goal_title && <p className="assistant-roadmap-note">Parcours calculé à partir de {roadmap.goal_type === "target_job" ? "cette offre réelle publiée" : "vos compétences sélectionnées"}. La progression indique l’apprentissage déclaré, pas une maîtrise validée.</p>}
        {roadmap && <>
          {proposals.map((proposal) => <section className="assistant-roadmap-section" key={proposal.id} aria-label="Proposition de mise à jour">
            <h3>Proposition à examiner</h3><strong>{proposal.title}</strong><p>{proposal.explanation}</p>
            {proposal.target_offer_id && <small>Offre publiée · {proposal.target_offer_id}</small>}
            {proposal.skills.length > 0 && <small>Compétences proposées : {proposal.skills.join(", ")}</small>}
            <div className="assistant-dialog-actions"><button className="button button--primary" disabled={busy} onClick={() => void decideProposal(proposal, "accepted")}>Accepter</button><button className="button button--secondary" disabled={busy} onClick={() => void decideProposal(proposal, "rejected")}>Rejeter</button></div>
          </section>)}
          <section className="assistant-roadmap-section"><h3>Compétences prioritaires</h3>
            {roadmap.target_offer_id && onNavigate && <button className="button button--secondary button--small" onClick={() => onNavigate("PrÃ©parer un entretien")}>Explorer les évaluations disponibles</button>}
            {roadmap.steps.length ? roadmap.steps.map((step) => <article className="assistant-roadmap-step" key={step.skill_key}>
              <div><strong>{step.skill}</strong><small>{step.required_by.length ? `Demandée par ${step.required_by.join(", ")}` : "Compétence choisie pour votre objectif"}</small></div>
              <label><input type="checkbox" checked={step.completed} disabled={busy} onChange={(event) => void toggleStep(step.skill, event.target.checked)}/> Apprentissage terminé</label>
            </article>) : <p className="assistant-roadmap-note">Aucune compétence manquante n’a été trouvée pour cet objectif.</p>}
          </section>
          <section className="assistant-roadmap-section"><h3>Projets pratiques</h3>
            {roadmap.steps.length > 0 && <form className="assistant-roadmap-goal" onSubmit={(event) => void addProject(event)}>
              <label><span>Compétence</span><select className="input" required value={projectSkill} onChange={(event) => setProjectSkill(event.target.value)}><option value="">Choisir une compétence</option>{roadmap.steps.map((step) => <option key={step.skill_key} value={step.skill}>{step.skill}</option>)}</select></label>
              <label><span>Nom du projet</span><input className="input" required minLength={2} maxLength={160} value={projectTitle} onChange={(event) => setProjectTitle(event.target.value)} /></label>
              <label><span>Description ou résultat attendu</span><textarea className="input" required maxLength={3000} value={projectDescription} onChange={(event) => setProjectDescription(event.target.value)} /></label>
              <button className="button button--primary" disabled={busy || !projectSkill}>Ajouter le projet</button>
            </form>}
            {projects.map((project) => <article className="assistant-roadmap-step" key={project.id}><div><strong>{project.title}</strong><small>{project.skill} · {project.description}</small></div><select className="input" aria-label={`État de ${project.title}`} value={project.status} disabled={busy} onChange={(event) => void changeProjectStatus(project, event.target.value as CandidateRoadmapProject["status"])}><option value="planned">À commencer</option><option value="in_progress">En cours</option><option value="submitted">Soumis pour validation</option></select></article>)}
            {!projects.length && <p className="assistant-roadmap-note">Aucun projet pratique pour le moment.</p>}
            <p className="assistant-roadmap-note">Un projet soumis reste en attente de validation; son statut ne confirme pas une maîtrise.</p>
          </section>
          <section className="assistant-roadmap-section"><h3>Évaluations</h3>
            {assessments.length ? assessments.map((assessment) => <article className="assistant-roadmap-step" key={assessment.assessment_id}><div><strong>{assessment.skill}</strong><small>{assessment.assessment_type === "technical" ? "Technique" : "Comportementale"} · {assessment.status === "completed" ? "Terminée" : "En cours"} · Score {assessment.score}/{assessment.max_score}</small></div></article>) : <p className="assistant-roadmap-note">Aucune évaluation commencée. Les résultats s’afficheront ici.</p>}
            {roadmap.target_offer_id && onNavigate && <button className="button button--secondary button--small" onClick={() => onNavigate("Préparer un entretien")}>Ouvrir les évaluations</button>}
            <p className="assistant-roadmap-note">Les résultats viennent des évaluations existantes et ne confirment pas automatiquement une maîtrise.</p>
          </section>
          <section className="assistant-roadmap-section"><h3>Formations du catalogue</h3>
            {recommendedCourses.length ? recommendedCourses.map((course) => {
              const enrollment = enrollments.find((item) => item.course_id === course.id && item.status !== "withdrawn");
              return <article className="assistant-roadmap-step" key={course.id}><div><strong>{course.title}</strong><small>{course.skills.join(" · ")}</small></div><button className="button button--secondary button--small" disabled={busy || Boolean(enrollment)} onClick={() => void enroll(course.id)}>{enrollment?.status === "completed" ? "Terminée" : enrollment ? "Inscrit" : "S’inscrire"}</button></article>;
            }) : <p className="assistant-roadmap-note">Aucune formation publiée ne correspond aux compétences restantes.</p>}
          </section>
        </>}
        {notice && <p className="assistant-roadmap-note" role="status">{notice}</p>}
        {error && <p className="workspace-error" role="alert">{error}</p>}
      </>}
    </div>
  </aside>;
}
