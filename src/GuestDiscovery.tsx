import { useEffect, useState, type FormEvent } from "react";
import { Search } from "lucide-react";
import { ApiError, fetchPublicJob, fetchPublicJobs, type JobOffer } from "./auth";
import { Button } from "./components/ui";

export function GuestDiscovery({ onApply }: { onApply: (offer: JobOffer) => void }) {
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

  async function search(searchQuery = query, searchLocation = location, searchOffset = 0) {
    setLoading(true);
    setError("");
    try {
      const result = await fetchPublicJobs({ q: searchQuery, location: searchLocation, offset: searchOffset });
      setJobs(result.items);
      setTotal(result.total);
      setOffset(result.offset);
    } catch (cause: unknown) {
      setError(cause instanceof ApiError ? cause.message : "Impossible de charger les offres publiques.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void search("", "");
  }, []);

  function submitSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSelectedJob(null);
    void search();
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

  return (
    <main className="guest-home">
      <header className="guest-home__header">
        <a className="brand" href="#accueil" aria-label="Mahara Match home">
          <span className="brand__mark" aria-hidden="true">m</span>
          <span className="brand__name">mahara<span>match</span></span>
        </a>
        <nav aria-label="Public navigation">
          <a href="#guest-jobs">Emplois</a>
          <a href="#guest-auth">Se connecter</a>
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
    </main>
  );
}
