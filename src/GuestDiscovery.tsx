import { useEffect, useRef, useState, type FormEvent } from "react";
import { ArrowLeft, ArrowRight, MapPin, Search } from "lucide-react";
import {
  ApiError,
  fetchPublicCourse,
  fetchPublicJob,
  fetchPublicJobs,
  fetchPublicMission,
  fetchPublicMissions,
  fetchPublicProfessional,
  fetchPublicProfessionals,
  fetchPublicService,
  fetchPublicServices,
  fetchPublicTraining,
  type JobOffer,
  type PublicCourse,
  type PublicMission,
  type PublicProfessional,
  type PublicService,
} from "./auth";
import { LanguageSwitch } from "./components/LanguageSwitch";
import { translate, type Language } from "./i18n";

type SearchFilters = { q: string; location: string; limit: number; offset: number };
type PublicPage<T> = { items: T[]; total: number; limit: number; offset: number };
type SearchFunction<T> = (filters: SearchFilters) => Promise<PublicPage<T>>;
type CategoryState<T> = {
  items: T[];
  total: number;
  offset: number;
  loading: boolean;
  error: string;
  loaded: boolean;
};
type CategoryKey = "jobs" | "professionals" | "services" | "training" | "missions";
type GuestTab = "all" | CategoryKey;
type GuestDetail =
  | { type: "jobs"; item: JobOffer }
  | { type: "professionals"; item: PublicProfessional }
  | { type: "services"; item: PublicService }
  | { type: "training"; item: PublicCourse }
  | { type: "missions"; item: PublicMission };
type GuestCard = {
  id: string;
  type: CategoryKey;
  title: string;
  location?: string | null;
  description?: string | null;
  meta?: string | null;
  figure?: string | null;
  skills: string[];
  action: string;
  open: () => void;
};

const categoryLabels: Record<CategoryKey, string> = {
  jobs: "Emploi",
  professionals: "Professionnel",
  services: "Service",
  training: "Formation",
  missions: "Mission",
};
const tabLabels: Record<GuestTab, string> = {
  all: "Tout",
  jobs: "Emplois",
  professionals: "Professionnels",
  services: "Services",
  training: "Formations",
  missions: "Missions",
};
const tabHeadings: Record<GuestTab, string> = {
  all: "Tout découvrir",
  jobs: "Offres d’emploi",
  professionals: "Professionnels",
  services: "Services",
  training: "Formations",
  missions: "Missions et projets",
};
const guestValueLabels: Record<string, string> = {
  remote: "À distance",
  on_site: "Sur site",
  hybrid: "Hybride",
  flexible: "Flexible",
  online: "À distance",
  in_person: "En présentiel",
  fixed: "Forfait",
  hourly: "À l’heure",
  starting_at: "À partir de",
  quote: "Sur devis",
  negotiable: "Négociable",
  full_time: "Temps plein",
  part_time: "Temps partiel",
  internship: "Stage",
};

const searchJobs: SearchFunction<JobOffer> = (filters) => fetchPublicJobs(filters);
const searchProfessionals: SearchFunction<PublicProfessional> = (filters) =>
  fetchPublicProfessionals(filters);
const searchServices: SearchFunction<PublicService> = (filters) => fetchPublicServices(filters);
const searchTraining: SearchFunction<PublicCourse> = (filters) => fetchPublicTraining(filters);
const searchMissions: SearchFunction<PublicMission> = (filters) => fetchPublicMissions(filters);

function emptyCategory<T>(): CategoryState<T> {
  return { items: [], total: 0, offset: 0, loading: false, error: "", loaded: false };
}

function errorMessage(error: unknown, fallback: string): string {
  return error instanceof ApiError ? error.message : fallback;
}

async function loadCategory<T>(
  search: SearchFunction<T>,
  query: string,
  location: string,
  limit: number,
  offset = 0,
  fallback = "Impossible de charger les résultats publics.",
): Promise<CategoryState<T>> {
  try {
    const result = await search({ q: query, location, limit, offset });
    return {
      items: Array.isArray(result?.items) ? result.items : [],
      total: Number.isFinite(result?.total) ? result.total : 0,
      offset: Number.isFinite(result?.offset) ? result.offset : offset,
      loading: false,
      error: "",
      loaded: true,
    };
  } catch (error: unknown) {
    return { ...emptyCategory<T>(), loading: false, error: errorMessage(error, fallback), loaded: true };
  }
}

function formatAmount(value: number | string | null | undefined): string | undefined {
  if (value === null || value === undefined || value === "") return undefined;
  return `${value} TND`;
}

function formatRange(
  minimum: number | string | null | undefined,
  maximum: number | string | null | undefined,
): string | undefined {
  const min = formatAmount(minimum);
  const max = formatAmount(maximum);
  if (min && max) return `${min} – ${max}`;
  return min || max;
}

function displayValue(value: string | null | undefined, language: Language): string | undefined {
  if (!value) return undefined;
  return translate(language, guestValueLabels[value] ?? value.replace(/_/g, " "));
}

function availabilityText(value: unknown, language: Language): string {
  if (value === null || value === undefined) return "";
  if (typeof value === "boolean") return translate(language, value ? "Oui" : "Non");
  if (typeof value === "string" || typeof value === "number") return String(value);
  if (Array.isArray(value)) return value.map((item) => availabilityText(item, language)).filter(Boolean).join(", ");
  if (typeof value === "object") {
    return Object.entries(value)
      .map(([key, item]) => `${key} : ${availabilityText(item, language)}`)
      .filter((entry) => !entry.endsWith(" : "))
      .join(" · ");
  }
  return "";
}

export function GuestDiscovery({
  language = "fr",
  onLanguageChange = () => {},
  onApply,
  onRequestService,
}: {
  language?: Language;
  onLanguageChange?: (language: Language) => void;
  onApply: (offer: JobOffer) => void;
  onRequestService: (service: PublicService) => void;
}) {
  const t = (text: string) => translate(language, text);
  const [query, setQuery] = useState("");
  const [location, setLocation] = useState("");
  const [activeTab, setActiveTab] = useState<GuestTab>("all");
  const [jobs, setJobs] = useState<CategoryState<JobOffer>>(emptyCategory);
  const [professionals, setProfessionals] =
    useState<CategoryState<PublicProfessional>>(emptyCategory);
  const [services, setServices] = useState<CategoryState<PublicService>>(emptyCategory);
  const [training, setTraining] = useState<CategoryState<PublicCourse>>(emptyCategory);
  const [missions, setMissions] = useState<CategoryState<PublicMission>>(emptyCategory);
  const [detail, setDetail] = useState<GuestDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState("");
  const previousScroll = useRef(0);
  const initialSearchStarted = useRef(false);

  async function searchAll(searchQuery: string, searchLocation: string) {
    setJobs((current) => ({ ...current, loading: true, error: "" }));
    setProfessionals((current) => ({ ...current, loading: true, error: "" }));
    setServices((current) => ({ ...current, loading: true, error: "" }));
    setTraining((current) => ({ ...current, loading: true, error: "" }));
    setMissions((current) => ({ ...current, loading: true, error: "" }));
    const [jobResults, professionalResults, serviceResults, trainingResults, missionResults] =
      await Promise.all([
        loadCategory(searchJobs, searchQuery, searchLocation, 20, 0, "Impossible de charger les offres publiques."),
        loadCategory(searchProfessionals, searchQuery, searchLocation, 6, 0, "Impossible de charger les profils publics."),
        loadCategory(searchServices, searchQuery, searchLocation, 6, 0, "Impossible de charger les services publics."),
        loadCategory(searchTraining, searchQuery, searchLocation, 6, 0, "Impossible de charger les formations publiques."),
        loadCategory(searchMissions, searchQuery, searchLocation, 6, 0, "Impossible de charger les missions publiques."),
      ]);
    setJobs(jobResults);
    setProfessionals(professionalResults);
    setServices(serviceResults);
    setTraining(trainingResults);
    setMissions(missionResults);
  }

  useEffect(() => {
    if (initialSearchStarted.current) return;
    initialSearchStarted.current = true;
    void searchAll("", "");
  }, []);

  function submitSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setDetail(null);
    void searchAll(query, location);
  }

  async function openDetail(item: GuestDetail) {
    previousScroll.current = window.scrollY;
    setDetail(item);
    setDetailLoading(true);
    setDetailError("");
    try {
      const loaded: GuestDetail =
        item.type === "jobs"
          ? { type: "jobs", item: await fetchPublicJob(item.item.id) }
          : item.type === "professionals"
            ? { type: "professionals", item: await fetchPublicProfessional(item.item.id) }
            : item.type === "services"
              ? { type: "services", item: await fetchPublicService(item.item.id) }
              : item.type === "training"
                ? { type: "training", item: await fetchPublicCourse(item.item.id) }
                : { type: "missions", item: await fetchPublicMission(item.item.id) };
      setDetail(loaded);
    } catch (error: unknown) {
      setDetailError(errorMessage(error, "Impossible de charger ce contenu."));
    } finally {
      setDetailLoading(false);
    }
  }

  function returnToResults() {
    setDetail(null);
    window.requestAnimationFrame(() => window.scrollTo(0, previousScroll.current));
  }

  async function loadMore(category: Exclude<CategoryKey, "jobs">) {
    const settings = { q: query, location, limit: 6 };
    if (category === "professionals") {
      setProfessionals((current) => ({ ...current, loading: true, error: "" }));
      const result = await loadCategory(
        searchProfessionals,
        settings.q,
        settings.location,
        settings.limit,
        professionals.offset + 6,
        "Impossible de charger les profils suivants.",
      );
      setProfessionals((current) => result.error
        ? { ...current, loading: false, error: result.error, loaded: true }
        : { ...result, items: [...current.items, ...result.items] });
    } else if (category === "services") {
      setServices((current) => ({ ...current, loading: true, error: "" }));
      const result = await loadCategory(
        searchServices,
        settings.q,
        settings.location,
        settings.limit,
        services.offset + 6,
        "Impossible de charger les services suivants.",
      );
      setServices((current) => result.error
        ? { ...current, loading: false, error: result.error, loaded: true }
        : { ...result, items: [...current.items, ...result.items] });
    } else if (category === "training") {
      setTraining((current) => ({ ...current, loading: true, error: "" }));
      const result = await loadCategory(
        searchTraining,
        settings.q,
        settings.location,
        settings.limit,
        training.offset + 6,
        "Impossible de charger les formations suivantes.",
      );
      setTraining((current) => result.error
        ? { ...current, loading: false, error: result.error, loaded: true }
        : { ...result, items: [...current.items, ...result.items] });
    } else {
      setMissions((current) => ({ ...current, loading: true, error: "" }));
      const result = await loadCategory(
        searchMissions,
        settings.q,
        settings.location,
        settings.limit,
        missions.offset + 6,
        "Impossible de charger les missions suivantes.",
      );
      setMissions((current) => result.error
        ? { ...current, loading: false, error: result.error, loaded: true }
        : { ...result, items: [...current.items, ...result.items] });
    }
  }

  async function changeJobPage(nextOffset: number) {
    setJobs((current) => ({ ...current, loading: true, error: "" }));
    const result = await loadCategory(
      searchJobs,
      query,
      location,
      20,
      nextOffset,
      "Impossible de charger les offres publiques.",
    );
    setJobs((current) => result.error
      ? { ...current, loading: false, error: result.error, loaded: true }
      : result);
  }

  const cardGroups: { type: CategoryKey; cards: GuestCard[]; state: CategoryState<unknown> }[] = [
    {
      type: "jobs",
      state: jobs,
      cards: jobs.items.map((item) => ({
        id: item.id,
        type: "jobs",
        title: item.title,
        location: item.location,
        description: item.description,
        meta: displayValue(item.employment_type, language),
        figure: formatRange(item.salary_min, item.salary_max),
        skills: item.required_skills,
        action: t("Voir l’offre"),
        open: () => void openDetail({ type: "jobs", item }),
      })),
    },
    {
      type: "professionals",
      state: professionals,
      cards: professionals.items.map((item) => ({
        id: item.id,
        type: "professionals",
        title: item.display_name,
        location: item.location,
        description: item.introduction,
        meta: t(item.available ? "Disponible" : "Indisponible"),
        figure: item.accepting_requests
          ? t("Accepte de nouvelles demandes")
          : item.service_area.join(", ") || undefined,
        skills: item.skills,
        action: t("Voir le profil"),
        open: () => void openDetail({ type: "professionals", item }),
      })),
    },
    {
      type: "services",
      state: services,
      cards: services.items.map((item) => ({
        id: item.id,
        type: "services",
        title: item.title,
        location: item.location,
        description: item.description,
        meta: displayValue(item.price_type, language),
        figure: item.price_min ? `${t("À partir de")} ${formatAmount(item.price_min)}` : undefined,
        skills: item.skills,
        action: t("Voir le service"),
        open: () => void openDetail({ type: "services", item }),
      })),
    },
    {
      type: "training",
      state: training,
      cards: training.items.map((item) => ({
        id: item.id,
        type: "training",
        title: item.title,
        location: item.location,
        description: item.summary,
        meta: displayValue(item.delivery_mode, language),
        figure:
          item.duration_hours !== null && item.duration_hours !== undefined
            ? `${item.duration_hours} h`
            : undefined,
        skills: item.skills,
        action: t("Voir la formation"),
        open: () => void openDetail({ type: "training", item }),
      })),
    },
    {
      type: "missions",
      state: missions,
      cards: missions.items.map((item) => ({
        id: item.id,
        type: "missions",
        title: item.title,
        location: item.location,
        description: item.description,
        meta: [displayValue(item.work_mode, language), displayValue(item.budget_type, language)].filter(Boolean).join(" · "),
        figure: formatRange(item.budget_min, item.budget_max),
        skills: item.required_skills,
        action: t("Voir la mission"),
        open: () => void openDetail({ type: "missions", item }),
      })),
    },
  ];

  const counts: Record<CategoryKey, number> = {
    jobs: jobs.total,
    professionals: professionals.total,
    services: services.total,
    training: training.total,
    missions: missions.total,
  };
  const states: Record<CategoryKey, CategoryState<unknown>> = {
    jobs,
    professionals,
    services,
    training,
    missions,
  };
  const activeCount =
    activeTab === "all" ? Object.values(counts).reduce((sum, count) => sum + count, 0) : counts[activeTab];
  const activeState =
    activeTab === "all" ? null : states[activeTab];
  const activeCards =
    activeTab === "all"
      ? cardGroups.flatMap((group) => group.cards.slice(0, 6))
      : cardGroups.find((group) => group.type === activeTab)?.cards ?? [];
  const anyLoading = activeTab === "all"
    ? cardGroups.some((group) => group.state.loading)
    : activeState?.loading ?? false;
  const activeErrors = activeTab === "all"
    ? cardGroups.filter((group) => group.state.error)
    : cardGroups.filter((group) => group.type === activeTab && group.state.error);

  function renderCard(card: GuestCard) {
    return (
      <article className={`guest-card guest-card--${card.type}`} key={`${card.type}-${card.id}`}>
        <div className="guest-card__topline">
          <span className="guest-type-chip">
            <span className="guest-type-chip__dot" aria-hidden="true" />
            {t(categoryLabels[card.type])}
          </span>
          {card.meta && <span className="guest-card__meta">{card.meta}</span>}
        </div>
        <h3>{card.title}</h3>
        <p className="guest-card__location">
          <MapPin size={16} aria-hidden="true" />
          <span>{card.location || t("À distance")}</span>
        </p>
        {card.description && <p className="guest-card__description">{card.description}</p>}
        {card.skills.length > 0 && (
          <ul className="guest-card__skills" aria-label={t("Compétences")}>
            {card.skills.slice(0, 5).map((skill) => <li key={skill}>{skill}</li>)}
          </ul>
        )}
        <footer className="guest-card__footer">
          {card.figure && <strong>{card.figure}</strong>}
          <button type="button" className="guest-button guest-button--dark" onClick={card.open}>
            {card.action}
            <ArrowRight size={16} aria-hidden="true" />
          </button>
        </footer>
      </article>
    );
  }

  return (
    <main className="guest-experience">
      <section className="guest-hero-band">
        <header className="guest-header guest-content">
          <a className="guest-brand" href="#accueil" aria-label={t("Mahara Match, accueil")}>
            <span className="guest-brand__mark" aria-hidden="true">m</span>
            <span>mahara<span>match</span></span>
          </a>
          <nav className="guest-header__links" aria-label={t("Compte")}>
            <LanguageSwitch language={language} onChange={onLanguageChange} />
            <a href="#guest-auth">{t("Se connecter")}</a>
            <a className="guest-button guest-button--light" href="#guest-auth-signup">{t("Créer un compte")}</a>
          </nav>
        </header>
        <div className="guest-hero guest-content">
          <p className="guest-eyebrow">{t("MAHARA MATCH · LES OPPORTUNITÉS EN TUNISIE")}</p>
          <h1>{t("Qu’est-ce que vous recherchez ?")}</h1>
          <p className="guest-hero__subtitle">
            {t("Emplois, professionnels, services, formations et missions : trouvez votre prochaine opportunité.")}
          </p>
          <form className="guest-search" onSubmit={submitSearch}>
            <label>
              <span>{t("Métier, compétence ou mot-clé")}</span>
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder={t("Ex. développeur Python")}
              />
            </label>
            <label>
              <span>{t("Ville ou gouvernorat")}</span>
              <input
                value={location}
                onChange={(event) => setLocation(event.target.value)}
                placeholder={t("Ex. Tunis")}
              />
            </label>
            <button type="submit" className="guest-button guest-button--terracotta">
              <Search size={18} aria-hidden="true" />
              {t("Rechercher")}
            </button>
          </form>
        </div>
      </section>

      <div className="guest-content guest-main">
        {detail ? (
          <section className="guest-detail" aria-live="polite">
            <button type="button" className="guest-back-link" onClick={returnToResults}>
              <ArrowLeft size={17} aria-hidden="true" />
              {t("Retour aux résultats")}
            </button>
            {detailLoading ? (
              <p className="guest-loading" aria-live="polite">{t("Chargement du détail…")}</p>
            ) : detailError ? (
              <p className="guest-error" role="alert">{detailError}</p>
            ) : detail.type === "jobs" ? (
              <article aria-labelledby="guest-detail-title">
                <p className="guest-eyebrow">{t("OFFRE D’EMPLOI")}</p>
                <h2 id="guest-detail-title">{detail.item.title}</h2>
                <div className="guest-detail__columns">
                  <div className="guest-detail__primary">
                    <h3>{t("Description du poste")}</h3>
                    <p className="guest-detail__prose">{detail.item.description}</p>
                    {detail.item.required_skills.length > 0 && (
                      <div>
                        <h3>{t("Compétences demandées")}</h3>
                        <ul className="guest-detail__skills">
                          {detail.item.required_skills.map((skill) => <li key={skill}>{skill}</li>)}
                        </ul>
                      </div>
                    )}
                    {detail.item.preferred_skills && detail.item.preferred_skills.length > 0 && (
                      <div>
                        <h3>{t("Compétences appréciées")}</h3>
                        <ul className="guest-detail__skills">
                          {detail.item.preferred_skills.map((skill) => <li key={skill}>{skill}</li>)}
                        </ul>
                      </div>
                    )}
                  </div>
                  <aside className="guest-detail__aside" aria-label={t("Informations sur l’offre")}>
                    {formatRange(detail.item.salary_min, detail.item.salary_max) && (
                      <div><span>{t("Salaire")}</span><strong>{formatRange(detail.item.salary_min, detail.item.salary_max)}</strong></div>
                    )}
                    {detail.item.employment_type && (
                      <div><span>{t("Type de contrat")}</span><strong>{detail.item.employment_type}</strong></div>
                    )}
                    <div><span>{t("Lieu")}</span><strong>{detail.item.location || t("À distance")}</strong></div>
                    {detail.item.workplace_arrangement && (
                      <div><span>{t("Organisation du travail")}</span><strong>{detail.item.workplace_arrangement}</strong></div>
                    )}
                    <button
                      type="button"
                      className="guest-button guest-button--dark guest-detail__apply"
                      onClick={() => onApply(detail.item)}
                    >
                      {t("Se connecter pour postuler")}
                    </button>
                  </aside>
                </div>
              </article>
            ) : detail.type === "services" ? (
              <article className="guest-detail__panel">
                <p className="guest-eyebrow">{detail.item.category}</p>
                <h2 id="guest-detail-title">{detail.item.title}</h2>
                <p className="guest-card__location"><MapPin size={16} aria-hidden="true" />{detail.item.location || t("À distance")}</p>
                <p className="guest-detail__prose">{detail.item.description}</p>
                <ul className="guest-detail__skills">{detail.item.skills.map((skill) => <li key={skill}>{skill}</li>)}</ul>
                <p className="guest-detail__fact">
                  {t("Tarif")} : {displayValue(detail.item.price_type, language)}
                  {formatRange(detail.item.price_min, detail.item.price_max) && ` · ${formatRange(detail.item.price_min, detail.item.price_max)}`}
                </p>
                {detail.item.portfolio_items.map((item) => (
                  <p key={item.url}><a href={item.url} target="_blank" rel="noreferrer">{item.title}</a></p>
                ))}
                <button type="button" className="guest-button guest-button--dark" onClick={() => onRequestService(detail.item)}>
                  {t("Se connecter pour demander ce service")}
                </button>
              </article>
            ) : detail.type === "professionals" ? (
              <article className="guest-detail__panel">
                <p className="guest-eyebrow">{t("PROFESSIONNEL")}</p>
                <h2 id="guest-detail-title">{detail.item.display_name}</h2>
                <h3>{detail.item.headline}</h3>
                <p className="guest-card__location"><MapPin size={16} aria-hidden="true" />{detail.item.location || t("À distance")}</p>
                <p className="guest-detail__prose">{detail.item.introduction}</p>
                <p>{detail.item.skills.join(" · ")}</p>
                {detail.item.service_area.length > 0 && <p>{t("Zones desservies")} : {detail.item.service_area.join(" · ")}</p>}
                <p>{t(detail.item.available ? "Disponible" : "Indisponible")}{detail.item.accepting_requests ? ` · ${t("Accepte de nouvelles demandes")}` : ""}</p>
                {Object.keys(detail.item.availability).length > 0 && (
                  <div><h3>{t("Disponibilités")}</h3><ul className="guest-detail__availability">
                    {Object.entries(detail.item.availability).map(([key, value]) => (
                      <li key={key}><strong>{key}</strong>{availabilityText(value, language) && ` : ${availabilityText(value, language)}`}</li>
                    ))}
                  </ul></div>
                )}
                {detail.item.portfolio_items.map((item) => (
                  <p key={item.url}><a href={item.url} target="_blank" rel="noreferrer">{item.title}</a></p>
                ))}
                {detail.item.services.length > 0 && (
                  <div><h3>{t("Services publiés")}</h3>{detail.item.services.map((item) => <p key={item.id}>{item.title} — {item.category}</p>)}</div>
                )}
              </article>
            ) : detail.type === "training" ? (
              <article className="guest-detail__panel">
                <p className="guest-eyebrow">{t("FORMATION")}</p>
                <h2 id="guest-detail-title">{detail.item.title}</h2>
                <p className="guest-detail__prose">{detail.item.summary}</p>
                <p className="guest-card__location"><MapPin size={16} aria-hidden="true" />{detail.item.location || t("À distance")}</p>
                {detail.item.duration_hours !== null && detail.item.duration_hours !== undefined && <p>{t("Durée")} : {detail.item.duration_hours} h</p>}
                {detail.item.delivery_mode && <p>{t("Modalité")} : {displayValue(detail.item.delivery_mode, language)}</p>}
                {detail.item.price_tnd !== null && detail.item.price_tnd !== undefined && <p>{t("Prix")} : {detail.item.price_tnd} TND</p>}
                <ul className="guest-detail__skills">{detail.item.skills.map((skill) => <li key={skill}>{skill}</li>)}</ul>
              </article>
            ) : (
              <article className="guest-detail__panel">
                <p className="guest-eyebrow">{t("MISSION")} · {detail.item.category}</p>
                <h2 id="guest-detail-title">{detail.item.title}</h2>
                <p className="guest-card__location"><MapPin size={16} aria-hidden="true" />{detail.item.location || t("À distance")}</p>
                <p className="guest-detail__prose">{detail.item.description}</p>
                <ul className="guest-detail__skills">{detail.item.required_skills.map((skill) => <li key={skill}>{skill}</li>)}</ul>
                {formatRange(detail.item.budget_min, detail.item.budget_max) && <p>{t("Budget")} : {formatRange(detail.item.budget_min, detail.item.budget_max)}</p>}
                <p>{[displayValue(detail.item.work_mode, language), displayValue(detail.item.budget_type, language), detail.item.duration].filter(Boolean).join(" · ")}</p>
              </article>
            )}
          </section>
        ) : (
          <>
            <div className="guest-tabs" role="tablist" aria-label={t("Catégories de résultats")}>
              {(Object.keys(tabLabels) as GuestTab[]).map((tab) => (
                <button
                  type="button"
                  role="tab"
                  key={tab}
                  id={`guest-tab-${tab}`}
                  aria-selected={activeTab === tab}
                  aria-controls="guest-results-panel"
                  tabIndex={activeTab === tab ? 0 : -1}
                  className={activeTab === tab ? "guest-tab guest-tab--active" : "guest-tab"}
                  onClick={() => setActiveTab(tab)}
                  onKeyDown={(event) => {
                    const tabs = Object.keys(tabLabels) as GuestTab[];
                    const current = tabs.indexOf(tab);
                    const nextIndex =
                      event.key === "ArrowRight"
                        ? (current + 1) % tabs.length
                        : event.key === "ArrowLeft"
                          ? (current - 1 + tabs.length) % tabs.length
                          : event.key === "Home"
                            ? 0
                            : event.key === "End"
                              ? tabs.length - 1
                              : current;
                    if (nextIndex !== current) {
                      event.preventDefault();
                      const nextTab = tabs[nextIndex];
                      setActiveTab(nextTab);
                      document.getElementById(`guest-tab-${nextTab}`)?.focus();
                    }
                  }}
                >
                  {t(tabLabels[tab])}
                  <span>{tab === "all" ? Object.values(counts).reduce((sum, count) => sum + count, 0) : counts[tab]}</span>
                </button>
              ))}
            </div>

            <section id="guest-results-panel" role="tabpanel" aria-labelledby={`guest-tab-${activeTab}`} className="guest-results">
              <header className="guest-results__heading">
                <div>
                  <p className="guest-eyebrow">{t("VOTRE PROCHAINE OPPORTUNITÉ")}</p>
                  <h2>{t(tabHeadings[activeTab])}</h2>
                </div>
                <span className="guest-results__count" aria-live="polite">
                  {activeCount} {t(activeCount === 1 ? "résultat" : "résultats")}
                </span>
              </header>

              {activeErrors.map((group) => (
                <p className="guest-error" role="alert" key={group.type}>
                  {t(group.state.error)}
                </p>
              ))}
              {anyLoading && (
                <p className="guest-loading" aria-live="polite">
                  {t(activeCards.length === 0 ? "Chargement des résultats…" : "Actualisation des résultats…")}
                </p>
              )}
              {activeTab === "all" && activeCards.length > 0 ? (
                <div className="guest-card-grid" aria-label={t("Résultats de toutes les catégories")}>
                  {cardGroups.map((group) => group.cards.length > 0 && (
                    <div className="guest-card-grid__group" key={group.type}>
                      <h3>
                        {t(tabLabels[group.type])}
                        <button type="button" onClick={() => setActiveTab(group.type)}>{t("Voir tout")} <ArrowRight size={15} aria-hidden="true" /></button>
                      </h3>
                      {group.cards.slice(0, 6).map(renderCard)}
                    </div>
                  ))}
                </div>
              ) : activeTab !== "all" && activeCards.length > 0 ? (
                <div className="guest-card-grid">
                  {activeCards.map(renderCard)}
                </div>
              ) : null}
              {!anyLoading && activeCards.length === 0 && activeErrors.length === 0 && (
                <div className="guest-empty">
                  <h3>{t("Aucun résultat pour cette recherche")}</h3>
                  <p>{t("Essayez un autre mot-clé, une autre ville ou une autre catégorie.")}</p>
                </div>
              )}

              {activeTab === "jobs" && jobs.total > 20 && (
                <div className="guest-pagination" aria-label={t("Pagination des offres")}>
                  <button
                    type="button"
                    className="guest-button guest-button--outline"
                    disabled={jobs.loading || jobs.offset === 0}
                    onClick={() => void changeJobPage(Math.max(0, jobs.offset - 20))}
                  >
                    <ArrowLeft size={16} aria-hidden="true" /> {t("Précédent")}
                  </button>
                  <span>{jobs.items.length ? jobs.offset + 1 : 0}–{Math.min(jobs.offset + jobs.items.length, jobs.total)} sur {jobs.total}</span>
                  <button
                    type="button"
                    className="guest-button guest-button--outline"
                    disabled={jobs.loading || jobs.offset + jobs.items.length >= jobs.total}
                    onClick={() => void changeJobPage(jobs.offset + 20)}
                  >
                    {t("Suivant")} <ArrowRight size={16} aria-hidden="true" />
                  </button>
                </div>
              )}
              {activeTab !== "all" && activeTab !== "jobs" && activeState && activeState.items.length < activeState.total && (
                <div className="guest-load-more">
                  <button
                    type="button"
                    className="guest-button guest-button--outline"
                    disabled={activeState.loading}
                    onClick={() => void loadMore(activeTab)}
                  >
                    {t(activeState.loading ? "Chargement…" : "Afficher plus de résultats")}
                  </button>
                </div>
              )}
            </section>
          </>
        )}
      </div>

      {!detail && (
        <>
          <section className="guest-bottom-cta">
            <div className="guest-content">
              <div>
                <p className="guest-eyebrow">{t("PRÊT·E À PASSER À L’ACTION ?")}</p>
                <h2>{t("Créez votre compte pour postuler, publier ou vous former")}</h2>
              </div>
              <a className="guest-button guest-button--terracotta" href="#guest-auth-signup">{t("Créer un compte")}</a>
            </div>
          </section>
          <footer className="guest-footer guest-content">
            <a className="guest-brand" href="#accueil" aria-label={t("Mahara Match, accueil")}>
              <span className="guest-brand__mark" aria-hidden="true">m</span>
              <span>mahara<span>match</span></span>
            </a>
            <span>{t("Les opportunités prennent forme ensemble.")}</span>
          </footer>
        </>
      )}
    </main>
  );
}
