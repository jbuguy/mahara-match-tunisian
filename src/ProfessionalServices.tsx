import { useEffect, useState, type FormEvent } from "react";
import { ApiError, createMyService, fetchMyProfessionalProfile, fetchMyServices, saveMyProfessionalProfile, updateMyService, updateMyServiceStatus, type ProfessionalProfile, type ServiceListing } from "./auth";
import { Button, Card } from "./components/ui";

const emptyProfile: Omit<ProfessionalProfile, "user_id" | "created_at" | "updated_at"> = {
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
  skills: string;
  location: string;
  service_mode: ServiceListing["service_mode"];
  price_type: ServiceListing["price_type"];
  price_min: string;
  price_max: string;
  portfolio_items: ServiceListing["portfolio_items"];
};

export function ProfessionalServicesPage({ token }: { token: string }) {
  const [profile, setProfile] = useState(emptyProfile);
  const [services, setServices] = useState<ServiceListing[]>([]);
  const [profileExists, setProfileExists] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [editingServiceId, setEditingServiceId] = useState<string | null>(null);
  const [service, setService] = useState<ServiceDraft>({ title: "", category: "", description: "", skills: "", location: "", service_mode: "remote", price_type: "quote", price_min: "", price_max: "", portfolio_items: [] });

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
        setProfile({
          display_name: savedProfile.display_name,
          headline: savedProfile.headline,
          introduction: savedProfile.introduction,
          photo_url: savedProfile.photo_url,
          location: savedProfile.location,
          languages: savedProfile.languages,
          skills: savedProfile.skills,
          years_experience: savedProfile.years_experience,
          visibility: savedProfile.visibility,
          available: savedProfile.available,
          accepting_requests: savedProfile.accepting_requests,
          availability: savedProfile.availability,
          service_area: savedProfile.service_area,
          portfolio_items: savedProfile.portfolio_items,
        });
      }
      setServices(Array.isArray(savedServices) ? savedServices : []);
    } catch (cause: unknown) {
      setError(cause instanceof ApiError ? cause.message : "Impossible de charger votre espace professionnel.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void load(); }, [token]);

  async function saveProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError("");
    try {
      const saved = await saveMyProfessionalProfile(token, {
        ...profile,
        location: profile.location || null,
        skills: profile.skills,
      });
      setProfileExists(true);
      setNotice("Profil professionnel enregistré.");
      setProfile((current) => ({ ...current, visibility: saved.visibility }));
    } catch (cause: unknown) {
      setError(cause instanceof ApiError ? cause.message : "Impossible d’enregistrer le profil.");
    } finally { setSaving(false); }
  }

  async function createService(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError("");
    try {
      const values = {
        ...service,
        skills: service.skills.split(",").map((item) => item.trim()).filter(Boolean),
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
      setService((current) => ({ ...current, title: "", category: "", description: "", skills: "", portfolio_items: [] }));
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
    <section className="market-page professional-services-page">
      <div className="eyebrow">SERVICES &amp; COMPÉTENCES</div>
      <h1>Mon profil professionnel</h1>
      <p className="market-page__intro">Présentez votre savoir-faire et publiez plusieurs services avec votre compte existant. Votre profil reste privé jusqu’à ce que vous choisissiez de le rendre public.</p>
      {error && <p className="auth-error" role="alert">{error}</p>}
      {notice && <p className="profile-save-notice" role="status">{notice}</p>}
      {loading ? <p aria-live="polite">Chargement…</p> : <>
        <Card as="section" className="professional-profile-form">
          <h2>{profileExists ? "Modifier mon profil" : "Créer mon profil professionnel"}</h2>
          <form className="workspace-form" onSubmit={(event) => void saveProfile(event)}>
            <label className="form-field"><span>Nom public</span><input required maxLength={120} value={profile.display_name} onChange={(event) => setProfile({ ...profile, display_name: event.target.value })} /></label>
            <label className="form-field"><span>Titre professionnel</span><input required maxLength={200} value={profile.headline} onChange={(event) => setProfile({ ...profile, headline: event.target.value })} /></label>
            <label className="form-field"><span>Présentation</span><textarea maxLength={5000} rows={4} value={profile.introduction} onChange={(event) => setProfile({ ...profile, introduction: event.target.value })} /></label>
            <label className="form-field"><span>Ville ou région</span><input maxLength={120} value={profile.location ?? ""} onChange={(event) => setProfile({ ...profile, location: event.target.value || null })} /></label>
            <label className="form-field"><span>Compétences, séparées par des virgules</span><input value={profile.skills.join(", ")} onChange={(event) => setProfile({ ...profile, skills: event.target.value.split(",").map((item) => item.trim()).filter(Boolean) })} /></label>
            <label className="form-field"><span>Années d’expérience (facultatif)</span><input type="number" min="0" max="80" value={profile.years_experience ?? ""} onChange={(event) => setProfile({ ...profile, years_experience: event.target.value ? Number(event.target.value) : null })} /></label>
            <label className="form-field"><span>Langues, séparées par des virgules</span><input value={profile.languages.join(", ")} onChange={(event) => setProfile({ ...profile, languages: event.target.value.split(",").map((item) => item.trim()).filter(Boolean) })} /></label>
            <label className="form-field"><span>Photo (URL)</span><input type="url" value={profile.photo_url ?? ""} onChange={(event) => setProfile({ ...profile, photo_url: event.target.value || null })} /></label>
            <label className="form-field"><span>Zones desservies (séparées par des virgules)</span><input value={profile.service_area.join(", ")} onChange={(event) => setProfile({ ...profile, service_area: event.target.value.split(",").map((item) => item.trim()).filter(Boolean) })} /></label>
            <label className="form-field"><span>Portfolio (un lien http(s) par ligne)</span><textarea rows={3} value={profile.portfolio_items.map((item) => item.url).join("\n")} onChange={(event) => setProfile({ ...profile, portfolio_items: event.target.value.split("\n").map((url) => url.trim()).filter(Boolean).map((url) => ({ title: url, url, description: "" })) })} /></label>
            <label className="form-field"><span>Disponibilités (JSON)</span><textarea rows={2} value={JSON.stringify(profile.availability)} onChange={(event) => { try { setProfile({ ...profile, availability: JSON.parse(event.target.value) as Record<string, unknown> }); } catch { /* retain last valid value */ } }} /></label>
            <label className="profile-entry__check"><input type="checkbox" checked={profile.visibility === "public"} onChange={(event) => setProfile({ ...profile, visibility: event.target.checked ? "public" : "private" })} /><span>Rendre mon profil visible dans la recherche publique</span></label>
            <label className="profile-entry__check"><input type="checkbox" checked={profile.available} onChange={(event) => setProfile({ ...profile, available: event.target.checked })} /><span>Je suis disponible</span></label>
            <label className="profile-entry__check"><input type="checkbox" checked={profile.accepting_requests} onChange={(event) => setProfile({ ...profile, accepting_requests: event.target.checked })} /><span>J’accepte de nouvelles demandes</span></label>
            <Button type="submit" disabled={saving}>{saving ? "Enregistrement…" : "Enregistrer le profil"}</Button>
          </form>
        </Card>
        <Card as="section" className="professional-service-form">
          <h2>{editingServiceId ? "Modifier le service" : "Publier un service"}</h2>
          <form className="workspace-form" onSubmit={(event) => void createService(event)}>
            <label className="form-field"><span>Nom du service</span><input required minLength={2} value={service.title} onChange={(event) => setService({ ...service, title: event.target.value })} /></label>
            <label className="form-field"><span>Catégorie</span><input required minLength={2} value={service.category} onChange={(event) => setService({ ...service, category: event.target.value })} /></label>
            <label className="form-field"><span>Description</span><textarea required minLength={10} rows={4} value={service.description} onChange={(event) => setService({ ...service, description: event.target.value })} /></label>
            <label className="form-field"><span>Compétences, séparées par des virgules</span><input value={service.skills} onChange={(event) => setService({ ...service, skills: event.target.value })} /></label>
            <label className="form-field"><span>Mode</span><select value={service.service_mode} onChange={(event) => setService({ ...service, service_mode: event.target.value as typeof service.service_mode })}><option value="remote">À distance</option><option value="provider_location">Chez le professionnel</option><option value="customer_location">Chez le client</option><option value="flexible">Flexible</option></select></label>
            <label className="form-field"><span>Ville (pour les services sur place)</span><input value={service.location} onChange={(event) => setService({ ...service, location: event.target.value })} /></label>
            <label className="form-field"><span>Portfolio du service (un lien http(s) par ligne)</span><textarea rows={2} value={service.portfolio_items.map((item) => item.url).join("\n")} onChange={(event) => setService({ ...service, portfolio_items: event.target.value.split("\n").map((url) => url.trim()).filter(Boolean).map((url) => ({ title: url, url, description: "" })) })} /></label>
            <label className="form-field"><span>Tarification</span><select value={service.price_type} onChange={(event) => setService({ ...service, price_type: event.target.value as typeof service.price_type })}><option value="quote">Sur devis</option><option value="fixed">Forfait</option><option value="hourly">À l’heure</option><option value="starting_at">À partir de</option><option value="negotiable">Négociable</option></select></label>
            <label className="form-field"><span>Prix minimum (TND, facultatif)</span><input type="number" min="0" step="0.01" value={service.price_min} onChange={(event) => setService({ ...service, price_min: event.target.value })} /></label>
            <label className="form-field"><span>Prix maximum (TND, facultatif)</span><input type="number" min="0" step="0.01" value={service.price_max} onChange={(event) => setService({ ...service, price_max: event.target.value })} /></label>
            <Button type="submit" disabled={saving || !profileExists}>{saving ? "Enregistrement…" : editingServiceId ? "Enregistrer les modifications" : "Créer le brouillon"}</Button>
            {editingServiceId && <Button variant="ghost" onClick={() => { setEditingServiceId(null); setService({ title: "", category: "", description: "", skills: "", location: "", service_mode: "remote", price_type: "quote", price_min: "", price_max: "", portfolio_items: [] }); }}>Annuler</Button>}
            {!profileExists && <p>Enregistrez d’abord votre profil professionnel.</p>}
          </form>
        </Card>
        <section className="professional-service-list" aria-labelledby="services-title">
          <h2 id="services-title">Mes services</h2>
          {services.length === 0 ? <p className="guest-home__empty">Aucun service créé pour le moment.</p> : services.map((item) => (
            <Card as="article" className="professional-service-item" key={item.id}>
              <div><span className="badge">{item.status}</span><h3>{item.title}</h3><p>{item.category} · {item.service_mode}</p><p>{item.description}</p></div>
              <div className="professional-service-item__actions">
                {item.status !== "archived" && <Button variant="secondary" onClick={() => { setEditingServiceId(item.id); setService({ title: item.title, category: item.category, description: item.description, skills: item.skills.join(", "), location: item.location ?? "", service_mode: item.service_mode, price_type: item.price_type, price_min: item.price_min ?? "", price_max: item.price_max ?? "", portfolio_items: item.portfolio_items }); window.scrollTo({ top: 0, behavior: "smooth" }); }}>Modifier</Button>}
                {item.status === "draft" && <Button onClick={() => void changeStatus(item, "published")}>Publier</Button>}
                {item.status === "published" && <Button variant="secondary" onClick={() => void changeStatus(item, "paused")}>Mettre en pause</Button>}
                {item.status === "paused" && <Button onClick={() => void changeStatus(item, "published")}>Reprendre</Button>}
                {item.status !== "archived" && <Button variant="ghost" onClick={() => void changeStatus(item, "archived")}>Archiver</Button>}
              </div>
            </Card>
          ))}
        </section>
      </>}
    </section>
  );
}
