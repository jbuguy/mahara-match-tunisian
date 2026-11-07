import { useEffect, useState, type FormEvent } from "react";
import { Search } from "lucide-react";
import {
  ApiError,
  fetchPublicCourse,
  fetchPublicJob,
  fetchPublicJobs,
  fetchPublicMissions,
  fetchPublicProfessional,
  fetchPublicProfessionals,
  fetchPublicService,
  fetchPublicServices,
  fetchPublicTraining,
  type JobOffer,
  type PublicCourse,
  type PublicProfessional,
  type PublicService,
  type PublicMission,
} from "./auth";
import { Button } from "./components/ui";

export function GuestDiscovery({ onApply, onRequestService }: { onApply: (offer: JobOffer) => void; onRequestService: (service: PublicService) => void }) {
  const [query, setQuery] = useState("");
  const [location, setLocation] = useState("");
  const [jobs, setJobs] = useState<JobOffer[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selectedJob, setSelectedJob] = useState<JobOffer | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState("");
  const [courses, setCourses] = useState<PublicCourse[]>([]);
  const [missions, setMissions] = useState<PublicMission[]>([]);
  const [services, setServices] = useState<PublicService[]>([]);
  const [professionals, setProfessionals] = useState<PublicProfessional[]>([]);
  const [selectedCourse, setSelectedCourse] = useState<PublicCourse | null>(null);
  const [selectedService, setSelectedService] = useState<PublicService | null>(null);
  const [selectedProfessional, setSelectedProfessional] = useState<PublicProfessional | null>(null);
  const [extraLoading, setExtraLoading] = useState(true);
  const [extraError, setExtraError] = useState("");
  const [serviceTotal, setServiceTotal] = useState(0);
  const [professionalTotal, setProfessionalTotal] = useState(0);
  const [courseTotal, setCourseTotal] = useState(0);
  const [missionTotal, setMissionTotal] = useState(0);
  const [serviceOffset, setServiceOffset] = useState(0);
  const [professionalOffset, setProfessionalOffset] = useState(0);
  const [courseOffset, setCourseOffset] = useState(0);

  async function search(searchQuery = query, searchLocation = location, searchOffset = 0) {
    setLoading(true);
    setError("");
    try {
      const result = await fetchPublicJobs({ q: searchQuery, location: searchLocation, offset: searchOffset });
      setJobs(Array.isArray(result?.items) ? result.items : []);
      setTotal(Number.isFinite(result?.total) ? result.total : 0);
      setOffset(Number.isFinite(result?.offset) ? result.offset : searchOffset);
    } catch (cause: unknown) {
      setError(cause instanceof ApiError ? cause.message : "Impossible de charger les offres publiques.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void search("", "");
    void searchMore("", "");
  }, []);

  async function searchMore(searchQuery = query, searchLocation = location) {
    setExtraLoading(true);
    setExtraError("");
    try {
      const [serviceResults, professionalResults, courseResults, missionResults] = await Promise.all([
        fetchPublicServices({ q: searchQuery, location: searchLocation, limit: 6 }),
        fetchPublicProfessionals({ q: searchQuery, location: searchLocation, limit: 6 }),
        fetchPublicTraining({ q: searchQuery, location: searchLocation, limit: 6 }),
        fetchPublicMissions({ q: searchQuery, location: searchLocation, limit: 6 }),
      ]);
      setServices(Array.isArray(serviceResults?.items) ? serviceResults.items : []);
      setProfessionals(Array.isArray(professionalResults?.items) ? professionalResults.items : []);
      setCourses(Array.isArray(courseResults?.items) ? courseResults.items : []);
      setMissions(Array.isArray(missionResults?.items) ? missionResults.items : []);
      setServiceTotal(Number.isFinite(serviceResults?.total) ? serviceResults.total : 0);
      setProfessionalTotal(Number.isFinite(professionalResults?.total) ? professionalResults.total : 0);
      setCourseTotal(Number.isFinite(courseResults?.total) ? courseResults.total : 0);
      setMissionTotal(Number.isFinite(missionResults?.total) ? missionResults.total : 0);
      setServiceOffset(Number.isFinite(serviceResults?.offset) ? serviceResults.offset : 0);
      setProfessionalOffset(Number.isFinite(professionalResults?.offset) ? professionalResults.offset : 0);
      setCourseOffset(Number.isFinite(courseResults?.offset) ? courseResults.offset : 0);
    } catch (cause: unknown) {
      setExtraError(cause instanceof ApiError ? cause.message : "Impossible de charger les autres contenus publics.");
    } finally {
      setExtraLoading(false);
    }
  }

  function submitSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSelectedJob(null);
    void search();
    void searchMore();
  }

  async function openJob(offer: JobOffer) {
    setSelectedJob(offer);
    setDetailLoading(true);
    setDetailError("");
    try {
      setSelectedJob(await fetchPublicJob(offer.id));
    } catch (cause: unknown) {
      setDetailError(cause instanceof ApiError ? cause.message : "Impossible de charger cette offre.");
    } finally {
      setDetailLoading(false);
    }
  }

  async function openService(service: PublicService) {
    setDetailLoading(true); setDetailError("");
    try { setSelectedService(await fetchPublicService(service.id)); }
    catch (cause: unknown) { setDetailError(cause instanceof ApiError ? cause.message : "Impossible de charger ce service."); }
    finally { setDetailLoading(false); }
  }

  async function openProfessional(profile: PublicProfessional) {
    setDetailLoading(true); setDetailError("");
    try { setSelectedProfessional(await fetchPublicProfessional(profile.id)); }
    catch (cause: unknown) { setDetailError(cause instanceof ApiError ? cause.message : "Impossible de charger ce profil."); }
    finally { setDetailLoading(false); }
  }

  async function openCourse(course: PublicCourse) {
    setDetailLoading(true); setDetailError("");
    try { setSelectedCourse(await fetchPublicCourse(course.id)); }
    catch (cause: unknown) { setDetailError(cause instanceof ApiError ? cause.message : "Impossible de charger cette formation."); }
    finally { setDetailLoading(false); }
  }

  async function loadMore(category: "services" | "professionals" | "training" | "missions") {
    setExtraLoading(true); setExtraError("");
    try {
      if (category === "services") {
        const offset = serviceOffset + 6;
        const result = await fetchPublicServices({ q: query, location, limit: 6, offset });
        setServices((current) => [...current, ...(Array.isArray(result?.items) ? result.items : [])]); setServiceOffset(Number.isFinite(result?.offset) ? result.offset : offset);
      } else if (category === "professionals") {
        const offset = professionalOffset + 6;
        const result = await fetchPublicProfessionals({ q: query, location, limit: 6, offset });
        setProfessionals((current) => [...current, ...(Array.isArray(result?.items) ? result.items : [])]); setProfessionalOffset(Number.isFinite(result?.offset) ? result.offset : offset);
      } else if (category === "training") {
        const offset = courseOffset + 6;
        const result = await fetchPublicTraining({ q: query, location, limit: 6, offset });
        setCourses((current) => [...current, ...(Array.isArray(result?.items) ? result.items : [])]); setCourseOffset(Number.isFinite(result?.offset) ? result.offset : offset);
      } else {
        const offset = missions.length;
        const result = await fetchPublicMissions({ q: query, location, limit: 6, offset });
        setMissions((current) => [...current, ...(Array.isArray(result?.items) ? result.items : [])]);
      }
    } catch (cause: unknown) {
      setExtraError(cause instanceof ApiError ? cause.message : "Impossible de charger la page suivante.");
    } finally { setExtraLoading(false); }
  }

  return (
    <main className="guest-home">
      <header className="guest-home__header">
        <a className="brand" href="#accueil" aria-label="Mahara Match home">
          <span className="brand__mark" aria-hidden="true">m</span>
          <span className="brand__name">mahara<span>match</span></span>
        </a>
        <nav aria-label="Public navigation">
          <a href="#guest-jobs">Emplois</a>
          <a href="#guest-services">Services</a>
          <a href="#guest-professionals">Professionnels</a>
          <a href="#guest-training">Formations</a>
          <a href="#guest-auth">Se connecter</a>
          <a href="#guest-auth">Créer un compte</a>
        </nav>
      </header>
      <section className="guest-home__hero">
        <div className="eyebrow">MAHARA MATCH</div>
        <h1>Qu’est-ce que vous recherchez&nbsp;?</h1>
        <p>Trouvez un emploi qui correspond à vos compétences et à votre région.</p>
        <form className="guest-home__search" onSubmit={submitSearch}>
          <label>
            <span>Métier, compétence ou mot-clé</span>
            <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Ex. développeur Python" />
          </label>
          <label>
            <span>Ville ou gouvernorat</span>
            <input value={location} onChange={(event) => setLocation(event.target.value)} placeholder="Ex. Tunis" />
          </label>
          <Button type="submit"><Search size={17} aria-hidden="true" /> Rechercher</Button>
        </form>
      </section>
      <section className="guest-home__results" id="guest-jobs" aria-labelledby="guest-jobs-title">
        {(selectedService || selectedProfessional || selectedCourse) && (
          <article className="guest-job-detail" aria-live="polite">
            <Button variant="secondary" onClick={() => { setSelectedService(null); setSelectedProfessional(null); setSelectedCourse(null); }}>Retour à la découverte</Button>
            {detailLoading ? <p>Chargement…</p> : detailError ? <p className="auth-error" role="alert">{detailError}</p> : selectedService ? (
              <><div className="eyebrow">{selectedService.category}</div><h2>{selectedService.title}</h2><p>{selectedService.location || "À distance"}</p><p>{selectedService.description}</p><p>Tarif : {selectedService.price_type}{selectedService.price_min ? ` · ${selectedService.price_min} TND` : ""}</p>{selectedService.portfolio_items.map((item) => <p key={item.url}><a href={item.url} target="_blank" rel="noreferrer">{item.title}</a></p>)}<Button onClick={() => onRequestService(selectedService)}>Demander ce service</Button></>
            ) : selectedProfessional ? (
              <><h2>{selectedProfessional.display_name}</h2><h3>{selectedProfessional.headline}</h3><p>{selectedProfessional.location}</p><p>{selectedProfessional.introduction}</p><p>{selectedProfessional.skills.join(" · ")}</p>{selectedProfessional.service_area.length > 0 && <p>Zones desservies : {selectedProfessional.service_area.join(" · ")}</p>}<p>{selectedProfessional.available ? "Disponible" : "Indisponible"}{selectedProfessional.accepting_requests ? " · Accepte de nouvelles demandes" : ""}</p>{Object.keys(selectedProfessional.availability).length > 0 && <p>Disponibilités : {JSON.stringify(selectedProfessional.availability)}</p>}{selectedProfessional.portfolio_items.map((item) => <p key={item.url}><a href={item.url} target="_blank" rel="noreferrer">{item.title}</a></p>)}<h3>Services publiés</h3>{selectedProfessional.services.map((item) => <p key={item.id}>{item.title} — {item.category}</p>)}</>
            ) : selectedCourse ? (
              <><div className="eyebrow">FORMATION</div><h2>{selectedCourse.title}</h2><p>{selectedCourse.summary}</p><p>{selectedCourse.location || "À distance"} · {selectedCourse.duration_hours} h</p><p>{selectedCourse.skills.join(" · ")}</p></>
            ) : null}
          </article>
        )}
        {selectedJob && (
          <article className="guest-job-detail" aria-labelledby="guest-job-detail-title">
            <Button variant="secondary" onClick={() => setSelectedJob(null)}>Retour aux offres</Button>
            {detailLoading ? <p aria-live="polite">Chargement de l’offre…</p> : detailError ? (
              <p className="auth-error" role="alert">{detailError}</p>
            ) : (
              <>
                <div className="eyebrow">{selectedJob.employment_type || "Emploi"}</div>
                <h2 id="guest-job-detail-title">{selectedJob.title}</h2>
                <p className="guest-job-card__location">{selectedJob.location}{selectedJob.workplace_arrangement ? ` · ${selectedJob.workplace_arrangement}` : ""}</p>
                {selectedJob.salary_min !== null && selectedJob.salary_min !== undefined && (
                  <p className="guest-job-detail__salary">Salaire : {selectedJob.salary_min}{selectedJob.salary_max !== null && selectedJob.salary_max !== undefined ? ` – ${selectedJob.salary_max}` : ""} TND</p>
                )}
                <p className="guest-job-detail__description">{selectedJob.description}</p>
                {selectedJob.required_skills.length > 0 && (
                  <div><h3>Compétences demandées</h3><ul>{selectedJob.required_skills.map((skill) => <li key={skill}>{skill}</li>)}</ul></div>
                )}
                <Button onClick={() => onApply(selectedJob)}>Se connecter pour postuler</Button>
              </>
            )}
          </article>
        )}
        {!selectedJob && <>
        <div className="guest-home__results-heading">
          <div><div className="eyebrow">OFFRES PUBLIÉES</div><h2 id="guest-jobs-title">Explorez les emplois</h2></div>
          {!loading && <span>{total} offre{total === 1 ? "" : "s"}</span>}
        </div>
        {loading ? <p aria-live="polite">Chargement des offres…</p> : error ? (
          <p className="auth-error" role="alert">{error}</p>
        ) : jobs.length === 0 ? (
          <p className="guest-home__empty">Aucune offre publiée ne correspond à cette recherche.</p>
        ) : (
          <div className="guest-home__job-grid">
            {jobs.map((offer) => (
              <article className="guest-job-card" key={offer.id}>
                <div className="eyebrow">{offer.employment_type || "Emploi"}</div>
                <h3>{offer.title}</h3>
                <p className="guest-job-card__location">{offer.location}{offer.workplace_arrangement ? ` · ${offer.workplace_arrangement}` : ""}</p>
                <p className="guest-job-card__description">{offer.description}</p>
                {offer.required_skills.length > 0 && <ul aria-label="Compétences demandées">{offer.required_skills.slice(0, 5).map((skill) => <li key={skill}>{skill}</li>)}</ul>}
                <Button variant="secondary" onClick={() => void openJob(offer)}>Voir l’offre</Button>
                <Button variant="secondary" onClick={() => onApply(offer)}>Se connecter pour postuler</Button>
              </article>
            ))}
          </div>
        )}
        {!loading && !error && total > 20 && (
          <div className="guest-home__pagination" aria-label="Pagination des offres">
            <Button variant="secondary" disabled={offset === 0} onClick={() => void search(query, location, Math.max(0, offset - 20))}>Précédent</Button>
            <span>{offset + 1}–{Math.min(offset + jobs.length, total)} sur {total}</span>
            <Button variant="secondary" disabled={offset + jobs.length >= total} onClick={() => void search(query, location, offset + 20)}>Suivant</Button>
          </div>
        )}
        </>}
      </section>
      {!selectedJob && !selectedService && !selectedProfessional && !selectedCourse && (
        <div className="guest-home__extra-sections">
          {extraError && <p className="auth-error" role="alert">{extraError}</p>}
          <section id="guest-missions" aria-labelledby="guest-missions-title"><div className="guest-home__results-heading"><div><div className="eyebrow">MISSIONS</div><h2 id="guest-missions-title">Missions et projets</h2></div></div>{extraLoading && missions.length === 0 ? <p>Chargement…</p> : missions.length ? <div className="guest-home__job-grid">{missions.map((item) => <article className="guest-job-card" key={item.id}><div className="eyebrow">{item.category}</div><h3>{item.title}</h3><p className="guest-job-card__location">{item.location || "À distance"} · {item.work_mode}</p><p className="guest-job-card__description">{item.description}</p><p>{item.required_skills.join(" · ")}</p><p>Budget : {item.budget_type}{item.budget_min ? ` · ${item.budget_min} TND` : ""}{item.budget_max ? ` – ${item.budget_max} TND` : ""}</p></article>)}</div> : <p className="guest-home__empty">Aucune mission publiée pour le moment.</p>}{missions.length < missionTotal && <Button variant="secondary" onClick={() => void loadMore("missions")} disabled={extraLoading}>Afficher plus de missions</Button>}</section>
          <section id="guest-services" aria-labelledby="guest-services-title"><div className="guest-home__results-heading"><div><div className="eyebrow">SERVICES</div><h2 id="guest-services-title">Services près de chez vous</h2></div></div>{extraLoading && services.length === 0 ? <p>Chargement…</p> : services.length ? <div className="guest-home__job-grid">{services.map((item) => <article className="guest-job-card" key={item.id}><div className="eyebrow">{item.category}</div><h3>{item.title}</h3><p className="guest-job-card__location">{item.location || "À distance"}</p><p className="guest-job-card__description">{item.description}</p><Button variant="secondary" onClick={() => void openService(item)}>Voir le service</Button></article>)}</div> : <p className="guest-home__empty">Aucun service public pour le moment.</p>}{services.length < serviceTotal && <Button variant="secondary" onClick={() => void loadMore("services")} disabled={extraLoading}>Afficher plus de services</Button>}</section>
          <section id="guest-professionals" aria-labelledby="guest-professionals-title"><div className="guest-home__results-heading"><div><div className="eyebrow">PROFESSIONNELS</div><h2 id="guest-professionals-title">Découvrez des professionnels</h2></div></div>{extraLoading && professionals.length === 0 ? <p>Chargement…</p> : professionals.length ? <div className="guest-home__job-grid">{professionals.map((profile) => <article className="guest-job-card" key={profile.id}><div className="eyebrow">{profile.available ? "Disponible" : "Indisponible"}</div><h3>{profile.display_name}</h3><p className="guest-job-card__location">{profile.headline} · {profile.location}</p><p className="guest-job-card__description">{profile.introduction}</p><Button variant="secondary" onClick={() => void openProfessional(profile)}>Voir le profil</Button></article>)}</div> : <p className="guest-home__empty">Aucun profil public pour le moment.</p>}{professionals.length < professionalTotal && <Button variant="secondary" onClick={() => void loadMore("professionals")} disabled={extraLoading}>Afficher plus de professionnels</Button>}</section>
          <section id="guest-training" aria-labelledby="guest-training-title"><div className="guest-home__results-heading"><div><div className="eyebrow">FORMATION</div><h2 id="guest-training-title">Formations recommandées</h2></div></div>{extraLoading && courses.length === 0 ? <p>Chargement…</p> : courses.length ? <div className="guest-home__job-grid">{courses.map((course) => <article className="guest-job-card" key={course.id}><div className="eyebrow">{course.delivery_mode}</div><h3>{course.title}</h3><p className="guest-job-card__location">{course.location || "À distance"} · {course.duration_hours} h</p><p className="guest-job-card__description">{course.summary}</p><Button variant="secondary" onClick={() => void openCourse(course)}>Voir la formation</Button></article>)}</div> : <p className="guest-home__empty">Aucune formation publiée pour le moment.</p>}{courses.length < courseTotal && <Button variant="secondary" onClick={() => void loadMore("training")} disabled={extraLoading}>Afficher plus de formations</Button>}</section>
        </div>
      )}
    </main>
  );
}
