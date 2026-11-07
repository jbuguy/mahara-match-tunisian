import { useEffect, useState } from "react";
import { ApiError, createServiceRequest, createServiceReview, fetchMyServiceRequests, fetchPublicServices, updateServiceRequestStatus, type PublicService, type ServiceRequest, type ServiceRequestStatus } from "./auth";
import { Button, Card } from "./components/ui";

type RequestDraft = { description: string; location: string; preferred_date: string; budget: string };
const emptyDraft: RequestDraft = { description: "", location: "", preferred_date: "", budget: "" };

export function ServiceRequestsWorkspace({ token, userId }: { token: string; userId: string }) {
  const [services, setServices] = useState<PublicService[]>([]);
  const [returnServiceId, setReturnServiceId] = useState<string | null>(null);
  const [requests, setRequests] = useState<ServiceRequest[]>([]);
  const [drafts, setDrafts] = useState<Record<string, RequestDraft>>({});
  const [reviewDrafts, setReviewDrafts] = useState<Record<string, { rating: number; comment: string }>>({});
  const [scopes, setScopes] = useState<Record<string, string>>({});
  const [reports, setReports] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  async function load() {
    setBusy(true); setError("");
    try {
      const [servicePage, myRequests] = await Promise.all([fetchPublicServices({ limit: 100 }), fetchMyServiceRequests(token)]);
      setServices(servicePage.items); setRequests(myRequests);
      const pendingServiceId = sessionStorage.getItem("mahara-match-return-service");
      if (pendingServiceId) {
        if (servicePage.items.some((item) => item.id === pendingServiceId)) {
          setReturnServiceId(pendingServiceId);
          sessionStorage.removeItem("mahara-match-return-service");
          requestAnimationFrame(() => document.getElementById(`service-card-${pendingServiceId}`)?.scrollIntoView({ behavior: "smooth", block: "center" }));
        } else {
          sessionStorage.removeItem("mahara-match-return-service");
          setError("Ce service n’est plus disponible. Vous pouvez choisir un autre service ci-dessous.");
        }
      }
    } catch (cause: unknown) { setError(cause instanceof ApiError ? cause.message : "Impossible de charger les demandes de service."); }
    finally { setBusy(false); }
  }
  useEffect(() => { void load(); }, [token]);
  useEffect(() => {
    if (returnServiceId) document.getElementById(`service-card-${returnServiceId}`)?.scrollIntoView({ behavior: "smooth", block: "center" });
  }, [returnServiceId, services]);

  async function submit(service: PublicService) {
    const draft = drafts[service.id] ?? emptyDraft;
    setError("");
    try {
      const saved = await createServiceRequest(token, service.id, { description: draft.description, location: draft.location || null, preferred_date: draft.preferred_date || null, budget: draft.budget || null, attachments: [] });
      setRequests((current) => [saved, ...current]); setDrafts((current) => ({ ...current, [service.id]: emptyDraft })); setNotice("Demande envoyée au professionnel.");
    } catch (cause: unknown) { setError(cause instanceof ApiError ? cause.message : "Impossible d’envoyer la demande."); }
  }

  async function transition(request: ServiceRequest, status: ServiceRequestStatus, extra: { agreed_scope?: string | null; report_reason?: string | null } = {}) {
    setError("");
    try {
      const updated = await updateServiceRequestStatus(token, request.id, status, extra);
      setRequests((current) => current.map((item) => item.id === updated.id ? updated : item));
      setNotice(status === "completed" ? "Fin de la prestation confirmée." : "Statut de la demande mis à jour.");
    } catch (cause: unknown) { setError(cause instanceof ApiError ? cause.message : "Impossible de mettre à jour la demande."); }
  }

  async function review(request: ServiceRequest) {
    const draft = reviewDrafts[request.id] ?? { rating: 5, comment: "" };
    setError("");
    try { await createServiceReview(token, request.id, { rating: draft.rating, comment: draft.comment || null }); setNotice("Merci pour votre avis."); }
    catch (cause: unknown) { setError(cause instanceof ApiError ? cause.message : "Impossible d’enregistrer cet avis."); }
  }

  function editDraft(id: string, key: keyof RequestDraft, value: string) {
    setDrafts((current) => ({ ...current, [id]: { ...(current[id] ?? emptyDraft), [key]: value } }));
  }

  return <main className="market-page service-requests-page">
    <div className="eyebrow">SERVICES</div><h1>Mes demandes de service</h1>
    <p className="market-page__intro">Vous pouvez demander un service avec votre compte existant. Aucun rôle ou profil client n’est nécessaire.</p>
    {error && <p className="auth-error" role="alert">{error}</p>}{notice && <p role="status">{notice}</p>}
    <section><h2>Découvrir et demander un service</h2>{busy && services.length === 0 ? <p>Chargement…</p> : services.length ? <div className="guest-home__job-grid">{services.map((service) => {
      const draft = drafts[service.id] ?? emptyDraft;
      const isOwnService = service.owner_user_id === userId;
      return <Card as="article" id={`service-card-${service.id}`} tabIndex={-1} className={returnServiceId === service.id ? "service-request-card--return-target" : ""} key={service.id}><div className="eyebrow">{service.category}</div><h3>{service.title}</h3><p>{service.description}</p><p>{service.location || "À distance"} · {service.service_mode}</p>{!isOwnService && <><label className="form-field"><span>Décrivez votre besoin</span><textarea minLength={10} value={draft.description} onChange={(event) => editDraft(service.id, "description", event.target.value)} /></label><label className="form-field"><span>Lieu souhaité</span><input value={draft.location} onChange={(event) => editDraft(service.id, "location", event.target.value)} /></label><label className="form-field"><span>Date souhaitée</span><input type="date" value={draft.preferred_date} onChange={(event) => editDraft(service.id, "preferred_date", event.target.value)} /></label><label className="form-field"><span>Budget indicatif (TND)</span><input type="number" min="0" step="0.01" value={draft.budget} onChange={(event) => editDraft(service.id, "budget", event.target.value)} /></label><Button disabled={busy || draft.description.trim().length < 10} onClick={() => void submit(service)}>Demander ce service</Button></>}</Card>;
    })}</div> : <p className="guest-home__empty">Aucun service public n’est disponible.</p>}</section>
    <section><h2>Demandes envoyées et reçues</h2>{busy && requests.length === 0 ? <p>Chargement…</p> : requests.length ? requests.map((request) => {
      const isProvider = request.provider_user_id === userId;
      const reviewDraft = reviewDrafts[request.id] ?? { rating: 5, comment: "" };
      return <Card as="article" key={request.id}><span className="badge">{request.status}</span><h3>{request.service_title}</h3><p>{request.description}</p><p>{request.location || "Lieu non précisé"}{request.preferred_date ? ` · ${request.preferred_date}` : ""}{request.budget ? ` · Budget ${request.budget} TND` : ""}</p>{request.agreed_scope && <p>Périmètre convenu : {request.agreed_scope}</p>}{request.report_reason && <p role="alert">Signalement : {request.report_reason}</p>}
        {isProvider && request.status === "requested" && <><label className="form-field"><span>Périmètre convenu (facultatif)</span><textarea value={scopes[request.id] ?? ""} onChange={(event) => setScopes((current) => ({ ...current, [request.id]: event.target.value }))} /></label><Button onClick={() => void transition(request, "accepted", { agreed_scope: scopes[request.id] || null })}>Accepter</Button><Button variant="secondary" onClick={() => void transition(request, "declined")}>Refuser</Button></>}
        {isProvider && request.status === "accepted" && <Button onClick={() => void transition(request, "in_progress", { agreed_scope: scopes[request.id] || request.agreed_scope })}>Commencer le travail</Button>}
        {isProvider && request.status === "in_progress" && <Button onClick={() => void transition(request, "completion_requested")}>Demander confirmation de fin</Button>}
        {!isProvider && request.status === "completion_requested" && <Button onClick={() => void transition(request, "completed")}>Confirmer la fin</Button>}
        {(request.status === "requested" || request.status === "accepted") && <Button variant="ghost" onClick={() => void transition(request, "cancelled")}>Annuler</Button>}
        {(request.status === "in_progress" || request.status === "completion_requested") && <><label className="form-field"><span>Signaler un problème</span><textarea value={reports[request.id] ?? ""} onChange={(event) => setReports((current) => ({ ...current, [request.id]: event.target.value }))} /></label><Button variant="secondary" disabled={(reports[request.id] ?? "").trim().length < 4} onClick={() => void transition(request, "disputed", { report_reason: reports[request.id] })}>Signaler</Button></>}
        {!isProvider && request.status === "completed" && <><label className="form-field"><span>Votre avis (1 à 5 étoiles)</span><select value={reviewDraft.rating} onChange={(event) => setReviewDrafts((current) => ({ ...current, [request.id]: { ...reviewDraft, rating: Number(event.target.value) } }))}>{[5, 4, 3, 2, 1].map((rating) => <option key={rating} value={rating}>{rating}</option>)}</select></label><label className="form-field"><span>Commentaire facultatif</span><textarea value={reviewDraft.comment} onChange={(event) => setReviewDrafts((current) => ({ ...current, [request.id]: { ...reviewDraft, comment: event.target.value } }))} /></label><Button variant="secondary" onClick={() => void review(request)}>Laisser un avis</Button></>}
      </Card>;
    }) : <p className="guest-home__empty">Vous n’avez pas encore de demande.</p>}</section>
  </main>;
}
