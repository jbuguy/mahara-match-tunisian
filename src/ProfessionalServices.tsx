import { useEffect, useRef, useState, type FormEvent } from "react";
import { ApiError, createMyService, fetchMyProfessionalProfile, fetchMyServices, saveMyProfessionalProfile, updateMyService, updateMyServiceStatus, type AssistantServiceSuggestion, type CandidateAssistantProfessionalSuggestion, type PortfolioItem, type ProfessionalProfile, type ServiceListing } from "./auth";
import { Button, Card } from "./components/ui";

const emptyProfile: Omit<ProfessionalProfile, "user_id" | "public_id" | "created_at" | "updated_at"> = {
  display_name: "",
  headline: "",
  introduction: "",
  photo_url: null,
  location: null,
  languages: [],
  skills: [],
  years_experience: null,
  visibility: "private",
  available: true,
  accepting_requests: true,
  availability: {},
  service_area: [],
  portfolio_items: [],
};

type ServiceDraft = {
  title: string;
  category: string;
  description: string;
  skills: string[];
  location: string;
  service_mode: ServiceListing["service_mode"];
  price_type: ServiceListing["price_type"];
  price_min: string;
  price_max: string;
  portfolio_items: ServiceListing["portfolio_items"];
};

type ProfessionalProfileDraft = Omit<ProfessionalProfile, "user_id" | "public_id" | "created_at" | "updated_at">;
type ProfessionalProfileSection = "identity" | "expertise" | "portfolio" | "availability";

export function ProfessionalServicesPage({
  token,
  embedded = false,
  sharedSkills,
  persistedSkills,
  onSharedSkillsChange,
  onSharedSkillsSaved,
  assistantDraftEvents = [],
}: {
  token: string;
  embedded?: boolean;
  sharedSkills?: string[];
  persistedSkills?: string[];
  onSharedSkillsChange?: (skills: string[]) => void;
  onSharedSkillsSaved?: (skills: string[]) => void;
  assistantDraftEvents?: CandidateAssistantProfessionalSuggestion[];
}) {
  const [profile, setProfile] = useState(emptyProfile);
  const [savedProfile, setSavedProfile] = useState<ProfessionalProfileDraft>(emptyProfile);
  const [services, setServices] = useState<ServiceListing[]>([]);
  const [profileExists, setProfileExists] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [availabilityError, setAvailabilityError] = useState("");
  const [editingServiceId, setEditingServiceId] = useState<string | null>(null);
  const [serviceEditorOpen, setServiceEditorOpen] = useState(false);
  const serviceEditorRef = useRef<HTMLDialogElement | null>(null);
  const appliedAssistantEvents = useRef(0);
  const [service, setService] = useState<ServiceDraft>({ title: "", category: "", description: "", skills: [], location: "", service_mode: "remote", price_type: "quote", price_min: "", price_max: "", portfolio_items: [] });

  async function load() {
    setLoading(true);
    setError("");
    try {
      const [savedProfile, savedServices] = await Promise.all([
        fetchMyProfessionalProfile(token).catch((cause: unknown) => {
          if (cause instanceof ApiError && cause.status === 404) return null;
          throw cause;
        }),
        fetchMyServices(token),
      ]);
      const hasCompleteProfileShape = savedProfile
        && Array.isArray(savedProfile.languages)
        && Array.isArray(savedProfile.skills)
        && Array.isArray(savedProfile.service_area)
        && Array.isArray(savedProfile.portfolio_items)
        && typeof savedProfile.availability === "object"
        && savedProfile.availability !== null;
      if (hasCompleteProfileShape) {
        setProfileExists(true);
        const draft = toProfessionalProfileDraft(savedProfile);
        setProfile(draft);
        setSavedProfile(draft);
      }
      setServices(Array.isArray(savedServices) ? savedServices : []);
    } catch (cause: unknown) {
      setError(cause instanceof ApiError ? cause.message : "Impossible de charger votre espace professionnel.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void load(); }, [token]);
  useEffect(() => {
    if (sharedSkills) setProfile((current) => ({ ...current, skills: sharedSkills }));
  }, [sharedSkills]);
  useEffect(() => {
    if (persistedSkills) setSavedProfile((current) => ({ ...current, skills: persistedSkills }));
  }, [persistedSkills]);
  useEffect(() => {
    if (loading) return;
    const pending = assistantDraftEvents.slice(appliedAssistantEvents.current);
    if (pending.length === 0) return;
    appliedAssistantEvents.current = assistantDraftEvents.length;
    for (const event of pending) {
      if (event.kind === "profile") {
        switch (event.field) {
          case "headline":
            setProfile((current) => ({ ...current, headline: event.value }));
            break;
          case "introduction":
            setProfile((current) => ({ ...current, introduction: event.value }));
            break;
          case "languages":
            setProfile((current) => ({ ...current, languages: event.value }));
            break;
          case "availability":
            setProfile((current) => ({ ...current, availability: event.value }));
            setAvailabilityError("");
            break;
        }
      } else {
        setEditingServiceId(null);
        setService(serviceFromAssistantSuggestion(event.suggestion));
        setServiceEditorOpen(true);
      }
    }
  }, [assistantDraftEvents, loading]);
  useEffect(() => {
    const dialog = serviceEditorRef.current;
    if (!dialog) return;
    if (serviceEditorOpen && !dialog.open) {
      if (typeof dialog.showModal === "function") dialog.showModal();
      else dialog.setAttribute("open", "");
    } else if (!serviceEditorOpen && dialog.open) {
      if (typeof dialog.close === "function") dialog.close();
      else dialog.removeAttribute("open");
    }
  }, [serviceEditorOpen, loading]);

  async function saveProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError("");
    try {
      const saved = await saveMyProfessionalProfile(token, {
        ...profile,
        location: profile.location || null,
        skills: sharedSkills ?? profile.skills,
      });
      setProfileExists(true);
      setNotice("Profil professionnel enregistré.");
      setSavedProfile(toProfessionalProfileDraft(saved));
      setProfile((current) => ({ ...current, visibility: saved.visibility, skills: saved.skills }));
      onSharedSkillsChange?.(saved.skills);
      onSharedSkillsSaved?.(saved.skills);
    } catch (cause: unknown) {
      setError(cause instanceof ApiError ? cause.message : "Impossible d’enregistrer le profil.");
    } finally { setSaving(false); }
  }

  async function saveProfileSection(section: ProfessionalProfileSection) {
    if (availabilityError && section === "availability") return;
    if (section === "portfolio" && profile.portfolio_items.some((item) =>
      !item.title.trim()
      || !item.url.trim()
      || !/^https?:\/\//i.test(item.url.trim()),
    )) {
      setError("Complétez le nom et le lien de chaque élément du portfolio, ou supprimez les éléments incomplets.");
      return;
    }

    const sectionValues = professionalProfileSectionValues(profile, section);
    const payload: ProfessionalProfileDraft = {
      ...savedProfile,
      ...sectionValues,
      skills: section === "expertise" ? (sharedSkills ?? profile.skills) : savedProfile.skills,
    };
    setSaving(true);
    setError("");
    try {
      const saved = await saveMyProfessionalProfile(token, payload);
      const savedDraft = toProfessionalProfileDraft(saved);
      const normalizedSection = professionalProfileSectionValues(savedDraft, section);
      setSavedProfile(savedDraft);
      setProfile((current) => ({ ...current, ...normalizedSection }));
      setProfileExists(true);
      if (section === "expertise") {
        onSharedSkillsChange?.(saved.skills);
        onSharedSkillsSaved?.(saved.skills);
      }
      setNotice(`${professionalProfileSectionLabel(section)} enregistrée.`);
    } catch (cause: unknown) {
      setError(cause instanceof ApiError ? cause.message : "Impossible d’enregistrer cette section du profil professionnel.");
    } finally {
      setSaving(false);
    }
  }

  async function createService(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError("");
    try {
      const values = {
        ...service,
        location: service.location || null,
        price_min: service.price_min ? service.price_min : null,
        price_max: service.price_max ? service.price_max : null,
      };
      const saved = editingServiceId
        ? await updateMyService(token, editingServiceId, values)
        : await createMyService(token, values);
      setServices((current) => editingServiceId
        ? current.map((item) => item.id === saved.id ? saved : item)
        : [saved, ...current]);
      setNotice(editingServiceId ? "Service mis à jour." : "Service créé comme brouillon.");
      setEditingServiceId(null);
      setService((current) => ({ ...current, title: "", category: "", description: "", skills: [], portfolio_items: [] }));
      setServiceEditorOpen(false);
    } catch (cause: unknown) {
      setError(cause instanceof ApiError ? cause.message : "Impossible de créer le service.");
    } finally { setSaving(false); }
  }

  async function changeStatus(item: ServiceListing, next: ServiceListing["status"]) {
    setError("");
    try {
      const updated = await updateMyServiceStatus(token, item.id, next);
      setServices((current) => current.map((row) => row.id === updated.id ? updated : row));
    } catch (cause: unknown) {
      setError(cause instanceof ApiError ? cause.message : "Impossible de modifier le statut du service.");
    }
  }

  return (
    <section id="professional-services" className={`market-page professional-services-page${embedded ? " professional-services-page--embedded" : ""}`}>
      {!embedded && <>
        <div className="eyebrow">SERVICES &amp; COMPÉTENCES</div>
        <h1>Mon profil professionnel</h1>
        <p className="market-page__intro">Présentez votre savoir-faire et publiez plusieurs services avec votre compte existant. Votre profil reste privé jusqu’à ce que vous choisissiez de le rendre public.</p>
      </>}
      {error && <p className="auth-error" role="alert">{error}</p>}
      {notice && <p className="profile-save-notice" role="status">{notice}</p>}
      {loading ? <p aria-live="polite">Chargement…</p> : <>
        <Card as="section" className="professional-profile-form">
          <h2>{embedded ? "Identité professionnelle et visibilité publique" : profileExists ? "Modifier mon profil" : "Créer mon profil professionnel"}</h2>
          <form className="workspace-form" onSubmit={(event) => void saveProfile(event)}>
            <section className="professional-edit-section">
              <header><div><h3>Identité professionnelle</h3><p>Votre nom public, votre titre et votre présentation.</p></div><Button type="button" variant="secondary" disabled={saving} onClick={() => void saveProfileSection("identity")}>Enregistrer l’identité</Button></header>
              <div className="professional-edit-section__fields">
                <label className="form-field"><span>Nom public</span><input required maxLength={120} value={profile.display_name} onChange={(event) => setProfile({ ...profile, display_name: event.target.value })} /></label>
                <label className="form-field"><span>Titre professionnel</span><input required maxLength={200} value={profile.headline} onChange={(event) => setProfile({ ...profile, headline: event.target.value })} /></label>
                <label className="form-field"><span>Présentation</span><textarea maxLength={5000} rows={4} value={profile.introduction} onChange={(event) => setProfile({ ...profile, introduction: event.target.value })} /></label>
                <label className="form-field"><span>Ville ou région</span><input maxLength={120} value={profile.location ?? ""} onChange={(event) => setProfile({ ...profile, location: event.target.value || null })} /></label>
                <label className="form-field"><span>Photo (URL)</span><input type="url" value={profile.photo_url ?? ""} onChange={(event) => setProfile({ ...profile, photo_url: event.target.value || null })} /></label>
              </div>
            </section>
            <section className="professional-edit-section">
              <header><div><h3>Compétences et langues</h3><p>Présentez vos savoir-faire, langues et zones desservies.</p></div><Button type="button" variant="secondary" disabled={saving || !profileExists} onClick={() => void saveProfileSection("expertise")}>Enregistrer les compétences et langues</Button></header>
              <div className="professional-edit-section__fields">
                <label className="form-field"><span>Compétences</span><TagEditor items={sharedSkills ?? profile.skills} onChange={(skills) => { setProfile({ ...profile, skills }); onSharedSkillsChange?.(skills); }} placeholder="Ajouter une compétence" /></label>
                <label className="form-field"><span>Années d’expérience (facultatif)</span><input type="number" min="0" max="80" value={profile.years_experience ?? ""} onChange={(event) => setProfile({ ...profile, years_experience: event.target.value ? Number(event.target.value) : null })} /></label>
                <label className="form-field"><span>Langues</span><TagEditor items={profile.languages} onChange={(languages) => setProfile({ ...profile, languages })} placeholder="Ajouter une langue" /></label>
                <label className="form-field"><span>Zones desservies</span><TagEditor items={profile.service_area} onChange={(service_area) => setProfile({ ...profile, service_area })} placeholder="Ajouter une zone" /></label>
              </div>
            </section>
            <section className="professional-edit-section">
              <header><div><h3>Portfolio</h3><p>Ajoutez des exemples de projets ou de réalisations.</p></div><Button type="button" variant="secondary" disabled={saving || !profileExists} onClick={() => void saveProfileSection("portfolio")}>Enregistrer le portfolio</Button></header>
              <PortfolioEditor items={profile.portfolio_items} onChange={(portfolio_items) => setProfile({ ...profile, portfolio_items })} />
            </section>
            <section className="professional-edit-section">
              <header><div><h3>Disponibilité et visibilité</h3><p>Choisissez si votre profil et vos services peuvent être découverts.</p></div><Button type="button" variant="secondary" disabled={saving || !profileExists || Boolean(availabilityError)} onClick={() => void saveProfileSection("availability")}>Enregistrer la disponibilité</Button></header>
              <div className="professional-edit-section__fields">
                <label className="form-field"><span>Disponibilités (JSON)</span><textarea rows={2} value={JSON.stringify(profile.availability)} aria-invalid={Boolean(availabilityError)} onChange={(event) => {
                  try {
                    const value: unknown = JSON.parse(event.target.value);
                    if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("Availability must be a JSON object.");
                    setProfile({ ...profile, availability: value as Record<string, unknown> });
                    setAvailabilityError("");
                  } catch {
                    setAvailabilityError("Saisissez un objet JSON valide pour les disponibilités.");
                  }
                }} />{availabilityError && <span className="form-error" role="alert">{availabilityError}</span>}</label>
                <label className="profile-entry__check"><input type="checkbox" checked={profile.visibility === "public"} onChange={(event) => setProfile({ ...profile, visibility: event.target.checked ? "public" : "private" })} /><span>Rendre mon profil visible dans la recherche publique</span></label>
                <label className="profile-entry__check"><input type="checkbox" checked={profile.available} onChange={(event) => setProfile({ ...profile, available: event.target.checked })} /><span>Je suis disponible</span></label>
                <label className="profile-entry__check"><input type="checkbox" checked={profile.accepting_requests} onChange={(event) => setProfile({ ...profile, accepting_requests: event.target.checked })} /><span>J’accepte de nouvelles demandes</span></label>
              </div>
            </section>
            <Button type="submit" disabled={saving || Boolean(availabilityError)}>{saving ? "Enregistrement…" : "Enregistrer le profil"}</Button>
          </form>
        </Card>
        <section className="professional-service-list" aria-labelledby="services-title">
          <header className="professional-service-list__header"><div><h2 id="services-title">Mes services</h2><p>Les services restent en brouillon jusqu’à leur publication.</p></div><Button type="button" disabled={!profileExists} onClick={() => { setEditingServiceId(null); setService({ title: "", category: "", description: "", skills: [], location: "", service_mode: "remote", price_type: "quote", price_min: "", price_max: "", portfolio_items: [] }); setServiceEditorOpen(true); }}>Créer un service</Button></header>
          {services.length === 0 ? <p className="guest-home__empty">Aucun service créé pour le moment.</p> : services.map((item) => (
            <Card as="article" className="professional-service-item" key={item.id}>
              <div><span className="badge">{item.status}</span><h3>{item.title}</h3><p>{item.category} · {item.service_mode}</p><p>{item.description}</p></div>
              <div className="professional-service-item__actions">
                {item.status !== "archived" && <Button variant="secondary" onClick={() => { setEditingServiceId(item.id); setService({ title: item.title, category: item.category, description: item.description, skills: item.skills, location: item.location ?? "", service_mode: item.service_mode, price_type: item.price_type, price_min: item.price_min ?? "", price_max: item.price_max ?? "", portfolio_items: item.portfolio_items }); setServiceEditorOpen(true); }}>Modifier</Button>}
                {item.status === "draft" && <Button onClick={() => void changeStatus(item, "published")}>Publier</Button>}
                {item.status === "published" && <Button variant="secondary" onClick={() => void changeStatus(item, "paused")}>Mettre en pause</Button>}
                {item.status === "paused" && <Button onClick={() => void changeStatus(item, "published")}>Reprendre</Button>}
                {item.status !== "archived" && <Button variant="ghost" onClick={() => void changeStatus(item, "archived")}>Archiver</Button>}
              </div>
            </Card>
          ))}
        </section>
        <dialog ref={serviceEditorRef} className="professional-service-dialog" onCancel={(event) => { event.preventDefault(); setServiceEditorOpen(false); }}>
          <Card as="section" className="professional-service-form">
            <h2>{editingServiceId ? "Modifier le service" : "Créer un service"}</h2>
            <form className="workspace-form" onSubmit={(event) => void createService(event)}>
              <label className="form-field"><span>Nom du service</span><input required minLength={2} value={service.title} onChange={(event) => setService({ ...service, title: event.target.value })} /></label>
              <label className="form-field"><span>Catégorie</span><input required minLength={2} value={service.category} onChange={(event) => setService({ ...service, category: event.target.value })} /></label>
              <label className="form-field"><span>Description</span><textarea required minLength={10} rows={4} value={service.description} onChange={(event) => setService({ ...service, description: event.target.value })} /></label>
              <label className="form-field"><span>Compétences</span><TagEditor items={service.skills} onChange={(skills) => setService({ ...service, skills })} placeholder="Ajouter une compétence" /></label>
              <label className="form-field"><span>Mode</span><select value={service.service_mode} onChange={(event) => setService({ ...service, service_mode: event.target.value as typeof service.service_mode })}><option value="remote">À distance</option><option value="provider_location">Chez le professionnel</option><option value="customer_location">Chez le client</option><option value="flexible">Flexible</option></select></label>
              <label className="form-field"><span>Ville (pour les services sur place)</span><input value={service.location} onChange={(event) => setService({ ...service, location: event.target.value })} /></label>
              <fieldset className="form-field professional-fieldset"><legend>Portfolio du service</legend><PortfolioEditor items={service.portfolio_items} onChange={(portfolio_items) => setService({ ...service, portfolio_items })} /></fieldset>
              <label className="form-field"><span>Tarification</span><select value={service.price_type} onChange={(event) => setService({ ...service, price_type: event.target.value as typeof service.price_type })}><option value="quote">Sur devis</option><option value="fixed">Forfait</option><option value="hourly">À l’heure</option><option value="starting_at">À partir de</option><option value="negotiable">Négociable</option></select></label>
              <label className="form-field"><span>Prix minimum (TND, facultatif)</span><input type="number" min="0" step="0.01" value={service.price_min} onChange={(event) => setService({ ...service, price_min: event.target.value })} /></label>
              <label className="form-field"><span>Prix maximum (TND, facultatif)</span><input type="number" min="0" step="0.01" value={service.price_max} onChange={(event) => setService({ ...service, price_max: event.target.value })} /></label>
              <Button type="submit" disabled={saving || !profileExists}>{saving ? "Enregistrement…" : editingServiceId ? "Enregistrer les modifications" : "Créer le brouillon"}</Button>
              <Button type="button" variant="ghost" onClick={() => setServiceEditorOpen(false)}>Annuler</Button>
              {!profileExists && <p>Enregistrez d’abord votre profil professionnel.</p>}
            </form>
          </Card>
        </dialog>
      </>}
    </section>
  );
}

function TagEditor({ items, onChange, placeholder }: { items: string[]; onChange: (items: string[]) => void; placeholder: string }) {
  const [draft, setDraft] = useState("");

  function addItem() {
    const value = draft.trim();
    if (value && !items.some((item) => item.toLocaleLowerCase() === value.toLocaleLowerCase())) {
      onChange([...items, value]);
    }
    setDraft("");
  }

  return <div className="professional-tag-editor">
    <div><input value={draft} onChange={(event) => setDraft(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") { event.preventDefault(); addItem(); } }} placeholder={placeholder} />
      <Button type="button" variant="secondary" disabled={!draft.trim()} onClick={addItem}>Ajouter</Button></div>
    <div className="professional-tag-editor__items">
      {items.map((item) => <span key={item}>{item}<button type="button" aria-label={`Retirer ${item}`} onClick={() => onChange(items.filter((value) => value !== item))}>×</button></span>)}
    </div>
  </div>;
}

function toProfessionalProfileDraft(profile: ProfessionalProfile): ProfessionalProfileDraft {
  return {
    display_name: profile.display_name,
    headline: profile.headline,
    introduction: profile.introduction,
    photo_url: profile.photo_url,
    location: profile.location,
    languages: profile.languages,
    skills: profile.skills,
    years_experience: profile.years_experience,
    visibility: profile.visibility,
    available: profile.available,
    accepting_requests: profile.accepting_requests,
    availability: profile.availability,
    service_area: profile.service_area,
    portfolio_items: profile.portfolio_items,
  };
}

function professionalProfileSectionValues(
  profile: ProfessionalProfileDraft,
  section: ProfessionalProfileSection,
): Partial<ProfessionalProfileDraft> {
  switch (section) {
    case "identity":
      return {
        display_name: profile.display_name,
        headline: profile.headline,
        introduction: profile.introduction,
        photo_url: profile.photo_url,
        location: profile.location,
      };
    case "expertise":
      return {
        skills: profile.skills,
        languages: profile.languages,
        years_experience: profile.years_experience,
        service_area: profile.service_area,
      };
    case "portfolio":
      return { portfolio_items: profile.portfolio_items };
    case "availability":
      return {
        availability: profile.availability,
        visibility: profile.visibility,
        available: profile.available,
        accepting_requests: profile.accepting_requests,
      };
  }
}

function professionalProfileSectionLabel(section: ProfessionalProfileSection): string {
  const labels = {
    identity: "L’identité professionnelle",
    expertise: "Les compétences et langues",
    portfolio: "Le portfolio",
    availability: "La disponibilité et la visibilité",
  };
  return labels[section];
}

function PortfolioEditor({ items, onChange }: { items: PortfolioItem[]; onChange: (items: PortfolioItem[]) => void }) {
  function updateItem(index: number, patch: Partial<PortfolioItem>) {
    onChange(items.map((item, current) => current === index ? { ...item, ...patch } : item));
  }

  return <div className="professional-portfolio-editor">
    {items.map((item, index) => <fieldset key={`${item.url}-${index}`}>
      <label><span>Nom du projet</span><input required value={item.title} onChange={(event) => updateItem(index, { title: event.target.value })} /></label>
      <label><span>Lien</span><input type="url" required value={item.url} onChange={(event) => updateItem(index, { url: event.target.value })} /></label>
      <label><span>Description</span><textarea rows={2} value={item.description} onChange={(event) => updateItem(index, { description: event.target.value })} /></label>
      <Button type="button" variant="ghost" aria-label={`Retirer ${item.title || "ce projet"}`} onClick={() => onChange(items.filter((_, current) => current !== index))}>Retirer</Button>
    </fieldset>)}
    <Button type="button" variant="secondary" disabled={items.length >= 12} onClick={() => onChange([...items, { title: "", url: "", description: "" }])}>Ajouter un projet</Button>
  </div>;
}

function serviceFromAssistantSuggestion(suggestion: AssistantServiceSuggestion): ServiceDraft {
  return {
    ...suggestion,
    location: "",
    price_min: "",
    price_max: "",
    portfolio_items: [],
  };
}
