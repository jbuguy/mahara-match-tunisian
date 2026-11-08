import { useEffect, useState, type FormEvent } from "react";
import { ApiError, createMission, fetchMissionProposals, fetchMyMissions, fetchPublicMissions, submitMissionProposal, updateMissionProposalStatus, updateMissionStatus, type Mission, type MissionProposal, type PublicMission } from "./auth";
import { Button, Card } from "./components/ui";

export function MissionsWorkspace({ token }: { token: string }) {
  const [mine, setMine] = useState<Mission[]>([]);
  const [publicMissions, setPublicMissions] = useState<PublicMission[]>([]);
  const [proposals, setProposals] = useState<MissionProposal[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [message, setMessage] = useState("");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState("");
  const [skills, setSkills] = useState("");
  const [location, setLocation] = useState("");
  const [workMode, setWorkMode] = useState<"remote" | "on_site" | "hybrid" | "flexible">("remote");
  const [budgetType, setBudgetType] = useState<"fixed" | "hourly" | "starting_at" | "quote" | "negotiable">("quote");
  const [budgetMin, setBudgetMin] = useState("");
  const [budgetMax, setBudgetMax] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  async function load() {
    setBusy(true); setError("");
    try {
      const [owned, available] = await Promise.all([fetchMyMissions(token), fetchPublicMissions({ limit: 50 })]);
      setMine(owned); setPublicMissions(available.items);
    } catch (cause: unknown) { setError(cause instanceof ApiError ? cause.message : "Impossible de charger les missions."); }
    finally { setBusy(false); }
  }
  useEffect(() => { void load(); }, [token]);

  async function publish(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError("");
    try {
      const draft = await createMission(token, { organisation_id: null, title, description, category, required_skills: skills.split(",").map((item) => item.trim()).filter(Boolean), location: location || null, work_mode: workMode, budget_type: budgetType, budget_min: budgetMin || null, budget_max: budgetMax || null, expected_start_date: null, deadline: null, duration: null, workers_needed: 1 });
      const published = await updateMissionStatus(token, draft.id, "published");
      setMine((current) => [published, ...current]); setTitle(""); setDescription(""); setCategory(""); setSkills(""); setNotice("Mission publiée.");
      await load();
    } catch (cause: unknown) { setError(cause instanceof ApiError ? cause.message : "Impossible de publier cette mission."); }
    finally { setBusy(false); }
  }

  async function openProposals(mission: Mission) {
    setSelected(mission.id); setError("");
    try { setProposals(await fetchMissionProposals(token, mission.id)); }
    catch (cause: unknown) { setError(cause instanceof ApiError ? cause.message : "Impossible de charger les propositions."); }
  }

  async function propose(mission: PublicMission) {
    if (message.trim().length < 10) { setError("Votre proposition doit contenir au moins 10 caractères."); return; }
    setBusy(true); setError("");
    try { await submitMissionProposal(token, mission.id, { message, proposed_price: null, estimated_duration: null, portfolio_references: [], availability: null }); setMessage(""); setNotice("Proposition envoyée au donneur d’ordre."); }
    catch (cause: unknown) { setError(cause instanceof ApiError ? cause.message : "Impossible d’envoyer la proposition."); }
    finally { setBusy(false); }
  }

  async function changeProposal(missionId: string, proposal: MissionProposal, status: "under_review" | "accepted" | "rejected") {
    try { const next = await updateMissionProposalStatus(token, missionId, proposal.id, status); setProposals((rows) => rows.map((row) => row.id === next.id ? next : row)); }
    catch (cause: unknown) { setError(cause instanceof ApiError ? cause.message : "Impossible de mettre à jour la proposition."); }
  }

  return <main className="market-page">
    <div className="eyebrow">MISSIONS INDÉPENDANTES</div><h1>Publier ou proposer mes services</h1>
    <p className="market-page__intro">Les missions sont gérées séparément des offres d’emploi et des candidatures.</p>
    {error && <p className="auth-error" role="alert">{error}</p>}{notice && <p role="status">{notice}</p>}
    <Card as="section"><h2>Publier une mission</h2><form className="workspace-form" onSubmit={(event) => void publish(event)}>
      <label className="form-field"><span>Titre</span><input required minLength={3} maxLength={160} value={title} onChange={(event) => setTitle(event.target.value)} /></label>
      <label className="form-field"><span>Description</span><textarea required minLength={10} value={description} onChange={(event) => setDescription(event.target.value)} /></label>
      <label className="form-field"><span>Catégorie</span><input required minLength={2} value={category} onChange={(event) => setCategory(event.target.value)} /></label>
      <label className="form-field"><span>Compétences requises (séparées par des virgules)</span><input value={skills} onChange={(event) => setSkills(event.target.value)} /></label>
      <label className="form-field"><span>Lieu</span><input value={location} onChange={(event) => setLocation(event.target.value)} /></label>
      <label className="form-field"><span>Mode de travail</span><select value={workMode} onChange={(event) => setWorkMode(event.target.value as typeof workMode)}><option value="remote">À distance</option><option value="on_site">Sur place</option><option value="hybrid">Hybride</option><option value="flexible">Flexible</option></select></label>
      <label className="form-field"><span>Type de budget</span><select value={budgetType} onChange={(event) => setBudgetType(event.target.value as typeof budgetType)}><option value="quote">Sur devis</option><option value="fixed">Forfait</option><option value="hourly">À l’heure</option><option value="starting_at">À partir de</option><option value="negotiable">Négociable</option></select></label>
      <label className="form-field"><span>Budget minimum (TND)</span><input type="number" min="0" step="0.01" value={budgetMin} onChange={(event) => setBudgetMin(event.target.value)} /></label>
      <label className="form-field"><span>Budget maximum (TND)</span><input type="number" min="0" step="0.01" value={budgetMax} onChange={(event) => setBudgetMax(event.target.value)} /></label>
      <Button type="submit" disabled={busy}>Publier la mission</Button>
    </form></Card>
    <section><h2>Mes missions</h2>{busy && mine.length === 0 ? <p>Chargement…</p> : mine.length ? mine.map((mission) => <Card as="article" key={mission.id}><span className="badge">{mission.status}</span><h3>{mission.title}</h3><p>{mission.category} · {mission.location || "À distance"}</p><div className="professional-service-item__actions">{mission.status === "draft" && <Button onClick={() => void updateMissionStatus(token, mission.id, "published").then((item) => setMine((rows) => rows.map((row) => row.id === item.id ? item : row)))}>Publier</Button>}{mission.status === "published" && <Button onClick={() => void updateMissionStatus(token, mission.id, "in_progress").then((item) => setMine((rows) => rows.map((row) => row.id === item.id ? item : row)))}>Commencer</Button>}{mission.status === "in_progress" && <Button onClick={() => void updateMissionStatus(token, mission.id, "completed").then((item) => setMine((rows) => rows.map((row) => row.id === item.id ? item : row)))}>Confirmer la fin</Button>}{mission.status === "published" && <Button variant="secondary" onClick={() => void openProposals(mission)}>Voir les propositions</Button>}</div>{selected === mission.id && proposals.map((proposal) => <div key={proposal.id}><span className="badge">{proposal.status}</span><p>{proposal.message}</p><p>{proposal.proposed_price ? `${proposal.proposed_price} TND` : "Prix à convenir"} · {proposal.estimated_duration || "Durée non précisée"}</p>{["submitted", "under_review"].includes(proposal.status) && <><Button variant="secondary" onClick={() => void changeProposal(mission.id, proposal, "under_review")}>Étudier</Button><Button onClick={() => void changeProposal(mission.id, proposal, "accepted")}>Accepter</Button><Button variant="ghost" onClick={() => void changeProposal(mission.id, proposal, "rejected")}>Refuser</Button></>}</div>)}</Card>) : <p className="guest-home__empty">Vous n’avez pas encore publié de mission.</p>}</section>
    <section><h2>Missions ouvertes</h2>{publicMissions.filter((item) => !mine.some((owned) => owned.id === item.id)).map((mission) => <Card as="article" key={mission.id}><h3>{mission.title}</h3><p>{mission.category} · {mission.location || "À distance"}</p><p>{mission.description}</p><p>Compétences : {mission.required_skills.join(" · ") || "Non précisées"}</p><label className="form-field"><span>Votre proposition</span><textarea minLength={10} value={selected === mission.id ? message : ""} onFocus={() => setSelected(mission.id)} onChange={(event) => { setSelected(mission.id); setMessage(event.target.value); }} /></label><Button disabled={busy || selected !== mission.id} onClick={() => void propose(mission)}>Envoyer une proposition</Button></Card>)}</section>
  </main>;
}
