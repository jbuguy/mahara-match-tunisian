import { useEffect, useState, type FormEvent } from "react";
import { Archive, ArrowLeft, FolderPlus, Pencil, Trash2 } from "lucide-react";
import { Badge, Button, Card, EmptyState } from "./components/ui";
import {
  createEmployerPlanningSession,
  deleteEmployerPlanningSession,
  fetchEmployerPlanningSessions,
  updateEmployerPlanningSession,
  type EmployerPlanningSession,
  type EmployerPlanningSessionStatus,
} from "./auth";

const statusLabels: Record<EmployerPlanningSessionStatus, string> = {
  draft: "Brouillon",
  in_progress: "En cours",
  analysis_ready: "Analyse prête",
  completed: "Terminée",
  archived: "Archivée",
};

const projectTypeLabels: Record<EmployerPlanningSession["project_type"], string> = {
  new_project: "Nouveau projet",
  department: "Nouveau département",
  expansion: "Expansion",
  organisational_need: "Besoin organisationnel",
  other: "Autre besoin",
};

export function EmployerPlanningWorkspace({ token }: { token: string }) {
  const [sessions, setSessions] = useState<EmployerPlanningSession[]>([]);
  const [selected, setSelected] = useState<EmployerPlanningSession | null>(null);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [projectType, setProjectType] = useState<EmployerPlanningSession["project_type"]>("other");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function refresh(selectedId?: string) {
    const rows = await fetchEmployerPlanningSessions(token);
    setSessions(rows);
    const targetId = selectedId ?? selected?.id;
    setSelected(rows.find((item) => item.id === targetId) ?? null);
  }

  useEffect(() => {
    let cancelled = false;
    fetchEmployerPlanningSessions(token)
      .then((rows) => { if (!cancelled) setSessions(rows); })
      .catch((cause: unknown) => { if (!cancelled) setError(cause instanceof Error ? cause.message : "Impossible de charger les planifications."); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [token]);

  async function createSession(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(""); setBusy(true);
    try {
      const created = await createEmployerPlanningSession(token, {
        title, description: description.trim() || null, project_type: projectType,
      });
      setTitle(""); setDescription(""); setProjectType("other");
      await refresh(created.id);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Impossible de créer la planification.");
    } finally { setBusy(false); }
  }

  async function renameSession(item: EmployerPlanningSession) {
    setError(""); setBusy(true);
    try {
      await updateEmployerPlanningSession(token, item.id, { title: editTitle });
      setEditingId(null); await refresh(item.id);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Impossible de renommer la planification."); }
    finally { setBusy(false); }
  }

  async function archiveSession(item: EmployerPlanningSession) {
    setError(""); setBusy(true);
    try { await updateEmployerPlanningSession(token, item.id, { status: "archived" }); await refresh(); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Impossible d’archiver la planification."); }
    finally { setBusy(false); }
  }

  async function removeSession(item: EmployerPlanningSession) {
    if (!window.confirm(`Supprimer la planification « ${item.title} » et ses données ?`)) return;
    setError(""); setBusy(true);
    try { await deleteEmployerPlanningSession(token, item.id); await refresh(); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Impossible de supprimer la planification."); }
    finally { setBusy(false); }
  }

  if (loading) return <section className="market-page"><h1>Planification RH avec l’IA</h1><p aria-live="polite">Chargement des planifications…</p></section>;

  return <section className="market-page employer-planning-page">
    <div className="eyebrow">ESPACE EMPLOYEUR</div>
    <h1>Planification RH avec l’IA</h1>
    <p className="market-page__intro">Décrivez un projet et organisez les besoins en recrutement de votre entreprise.</p>
    {error && <p className="workspace-error" role="alert">{error}</p>}

    {selected ? <Card className="market-panel planning-session-detail">
      <Button variant="secondary" onClick={() => setSelected(null)}><ArrowLeft size={16}/> Toutes les planifications</Button>
      <div className="market-panel__heading"><div><div className="eyebrow">{projectTypeLabels[selected.project_type]}</div><h2>{selected.title}</h2></div><Badge>{statusLabels[selected.status]}</Badge></div>
      {selected.description && <p>{selected.description}</p>}
      <div className="planning-context-empty"><FolderPlus size={22}/><h3>Votre espace de projet</h3><p>La conversation avec l’assistant, le résumé du projet et les recommandations seront disponibles dans les prochaines étapes.</p></div>
      <small>Dernière activité : {new Date(selected.updated_at).toLocaleString("fr-FR")}</small>
    </Card> : <>
      <form className="workspace-form" onSubmit={(event) => void createSession(event)}>
        <Card className="market-panel">
          <h2>Nouvelle planification</h2>
          <label className="form-field"><span className="form-field__label">Nom du projet</span><input className="input" required minLength={2} maxLength={160} value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Ex. Lancement d’une équipe marketing"/></label>
          <label className="form-field"><span className="form-field__label">Type de besoin</span><select className="input" value={projectType} onChange={(event) => setProjectType(event.target.value as EmployerPlanningSession["project_type"])}>{Object.entries(projectTypeLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
          <label className="form-field organisation-form__wide"><span className="form-field__label">Description courte (facultatif)</span><textarea className="input workspace-textarea" maxLength={2000} value={description} onChange={(event) => setDescription(event.target.value)} placeholder="Quel projet ou besoin souhaitez-vous étudier ?"/></label>
          <div className="market-section-heading"><Button type="submit" disabled={busy || title.trim().length < 2}><FolderPlus size={16}/> Créer la planification</Button></div>
        </Card>
      </form>

      <div className="market-section-heading planning-list-heading"><div><h2>Vos planifications</h2><p>{sessions.length} projet{sessions.length === 1 ? "" : "s"}</p></div></div>
      {sessions.length === 0 ? <Card className="market-panel"><EmptyState title="Aucune planification pour le moment" description="Créez une planification pour commencer à préciser les besoins de votre prochain projet."/></Card> :
        <div className="market-list">{sessions.map((item) => <Card className="market-panel" key={item.id}>
          <div className="market-panel__heading"><div>{editingId === item.id ? <form className="planning-rename" onSubmit={(event) => { event.preventDefault(); void renameSession(item); }}><input className="input" aria-label="Nouveau nom du projet" value={editTitle} minLength={2} maxLength={160} onChange={(event) => setEditTitle(event.target.value)}/><Button type="submit" disabled={busy || editTitle.trim().length < 2}>Enregistrer</Button><Button variant="secondary" type="button" onClick={() => setEditingId(null)}>Annuler</Button></form> : <><h2>{item.title}</h2><p>{projectTypeLabels[item.project_type]} · Mis à jour le {new Date(item.updated_at).toLocaleDateString("fr-FR")}</p></>}</div><Badge>{statusLabels[item.status]}</Badge></div>
          {item.description && <p>{item.description}</p>}
          <div className="planning-session-actions"><Button variant="secondary" onClick={() => setSelected(item)}>{item.status === "archived" ? "Consulter" : "Ouvrir"}</Button>{item.status !== "archived" && <><Button variant="secondary" onClick={() => { setEditingId(item.id); setEditTitle(item.title); }} aria-label={`Renommer ${item.title}`}><Pencil size={15}/> Renommer</Button><Button variant="secondary" disabled={busy} onClick={() => void archiveSession(item)}><Archive size={15}/> Archiver</Button></>}<Button variant="secondary" disabled={busy} onClick={() => void removeSession(item)} aria-label={`Supprimer ${item.title}`}><Trash2 size={15}/> Supprimer</Button></div>
        </Card>)}</div>}
    </>}
  </section>;
}
