import { useEffect, useState, type FormEvent } from "react";
import { ArrowUpRight, BriefcaseBusiness, Search, UserPlus } from "lucide-react";
import { Badge, Button, Card, ChartFrame, DataTable, EmptyState } from "./components/ui";
import { LocationSelect } from "./components/LocationSelect";
import {
  ApiError,
  createTrainingCourse,
  createEmployerOrganisation,
  enrollInCourse,
  fetchAdminIndicators,
  fetchCandidateApplications,
  fetchCandidateOfferDecisions,
  respondToJobOffer,
  fetchCandidateEnrollments,
  fetchEmployerApplications,
  fetchEmployerApplicationDetail,
  fetchApplicationNotes,
  addApplicationNote,
  fetchApplicationEvaluation,
  saveApplicationEvaluation,
  createFormalOffer,
  fetchEmployerOffers,
  fetchEmployerOrganisation,
  fetchProviderCourseEnrollments,
  fetchPublishedCourses,
  fetchTrainingCourses,
  updateCourseEnrollmentStatus,
  updateEmployerApplicationStatus,
  withdrawCandidateApplication,
  updateEmployerOrganisation,
  searchEmployerCandidates,
  fetchTalentPools,
  createTalentPool,
  addCandidateToTalentPool,
  fetchTalentPoolMembers,
  fetchEmployerConversations,
  removeTalentPoolMember,
  ensureApplicationConversation,
  fetchConversationMessages,
  sendConversationMessage,
  fetchEmployerInterviews,
  createEmployerInterview,
  updateEmployerInterviewStatus,
  fetchEmployerNotifications,
  markEmployerNotificationRead,
  fetchNotificationPreferences,
  updateNotificationPreference,
  submitOrganisationVerification,
  fetchEmployerAnalytics,
  fetchPendingOrganisationVerifications,
  reviewOrganisationVerification,
  updateTrainingCourse,
  type AdminIndicators,
  type CourseDeliveryMode,
  type CourseEnrollment,
  type CourseEnrollmentStatus,
  type EmployerApplication,
  type EmployerApplicationDetail,
  type ApplicationNote,
  type ApplicationEvaluation,
  type JobOfferDecision,
  type JobApplication,
  type JobApplicationStatus,
  type OrganisationProfile,
  type ProviderCourseEnrollment,
  type TrainingCourse,
  type TrainingCourseDraft,
  type CandidateDiscovery,
  type TalentPool,
  type TalentPoolMember,
  type Conversation,
  type ConversationMessage,
  type EmployerInterview,
  type EmployerNotification,
  type NotificationPreference,
  type EmployerAnalytics,
  type OrganisationVerification,
} from "./auth";

function errorMessage(error: unknown): string {
  return error instanceof ApiError
    ? error.message
    : "Impossible de joindre le service. Vérifiez votre connexion.";
}

const applicationStatusLabels: Record<JobApplicationStatus, string> = {
  submitted: "Reçue",
  reviewing: "À l’étude",
  shortlisted: "Présélectionnée",
  interview: "Entretien",
  interview_completed: "Entretien terminé",
  offer_made: "Offre envoyée",
  interviewed: "Entretien réalisé",
  offered: "Offre proposée",
  hired: "Recrutée",
  rejected: "Non retenue",
  withdrawn: "Retirée",
};

const employerApplicationNextStatuses: Record<JobApplicationStatus, JobApplicationStatus[]> = {
  submitted: ["reviewing", "shortlisted", "interview", "hired", "rejected"],
  reviewing: ["shortlisted", "interview", "hired", "rejected"],
  shortlisted: ["reviewing", "interview", "hired", "rejected"],
  interview: ["interview_completed", "offer_made", "hired", "rejected"],
  interview_completed: ["offer_made", "hired", "rejected"],
  interviewed: ["offered", "hired", "rejected"],
  offered: ["hired", "rejected"],
  offer_made: ["hired", "rejected"],
  hired: [],
  rejected: [],
  withdrawn: [],
};

const jobOfferStatusLabels: Record<NonNullable<import("./auth").JobOffer["status"]>, string> = {
  draft: "Brouillon",
  published: "Publiée",
  paused: "En pause",
  closed: "Clôturée",
  expired: "Expirée",
  archived: "Archivée",
};

const enrollmentStatusLabels: Record<CourseEnrollmentStatus, string> = {
  enrolled: "Inscrit",
  completed: "Terminée",
  withdrawn: "Désinscrit",
};

const deliveryLabels: Record<CourseDeliveryMode, string> = {
  online: "À distance",
  in_person: "En présentiel",
  hybrid: "Hybride",
};

function formatDate(value: string | null): string {
  if (!value) return "À définir";
  return new Date(`${value.slice(0, 10)}T12:00:00`).toLocaleDateString("fr-FR");
}

function MetricCard({
  label,
  value,
  detail,
}: {
  label: string;
  value: string | number;
  detail: string;
}) {
  return (
    <Card className="market-metric">
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{detail}</small>
    </Card>
  );
}

export function AdminDashboardPage({ token }: { token: string }) {
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [appliedRange, setAppliedRange] = useState({ startDate: "", endDate: "" });
  const [indicators, setIndicators] = useState<AdminIndicators | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    setIsLoading(true);
    setError("");
    fetchAdminIndicators(token, appliedRange.startDate, appliedRange.endDate)
      .then((result) => {
        if (!cancelled) setIndicators(result);
      })
      .catch((cause: unknown) => {
        if (!cancelled) setError(errorMessage(cause));
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [token, appliedRange]);

  function applyDateRange(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setAppliedRange({ startDate, endDate });
  }

  const maxStatusCount = Math.max(
    1,
    ...(indicators?.applications_by_status.map((item) => item.count) ?? []),
  );
  const maxSkillCount = Math.max(1, ...(indicators?.top_skills.map((item) => item.offer_count) ?? []));

  return (
    <section className="market-page">
      <div className="eyebrow">PILOTAGE AGRÉGÉ</div>
      <h1>Tableau de bord administration</h1>
      <p className="market-page__intro">
        Suivez l’activité, les compétences demandées et les résultats déclarés par les employeurs.
        Les données présentées sont agrégées et ne contiennent pas de profils individuels.
      </p>

      <div className="admin-overview-banner">
        <div className="admin-overview-banner__copy">
          <span className="admin-overview-banner__eyebrow">INDICATEURS DE LA PLATEFORME</span>
          <h2>Un aperçu de l’activité emploi et formation</h2>
          <p>Les chiffres et graphiques ci-dessous reflètent les données agrégées de la période sélectionnée.</p>
        </div>
        <div className="admin-overview-banner__visual" aria-hidden="true">
          <span /><span /><span /><span /><span /><span /><span />
          <i className="admin-overview-banner__line" />
        </div>
      </div>

      <form className="market-filter" onSubmit={applyDateRange}>
        <label className="form-field">
          <span className="form-field__label">Du</span>
          <input
            className="input"
            type="date"
            value={startDate}
            max={endDate || undefined}
            onChange={(event) => setStartDate(event.target.value)}
          />
        </label>
        <label className="form-field">
          <span className="form-field__label">Au</span>
          <input
            className="input"
            type="date"
            value={endDate}
            min={startDate || undefined}
            onChange={(event) => setEndDate(event.target.value)}
          />
        </label>
        <Button type="submit" disabled={isLoading}>Appliquer la période</Button>
      </form>

      {error && <p className="workspace-error" role="alert">{error}</p>}
      {isLoading && <p aria-live="polite">Chargement des indicateurs…</p>}
      {!isLoading && !error && indicators && (
        <>
          <p className="market-range">
            Période : {indicators.start_date ? formatDate(indicators.start_date) : "sans limite"}
            {" — "}
            {indicators.end_date ? formatDate(indicators.end_date) : "aujourd’hui"}
          </p>
          <div className="market-metrics">
            <MetricCard
              label="Candidats inscrits"
              value={indicators.candidate_registrations}
              detail="Comptes candidats créés pendant la période"
            />
            <MetricCard
              label="Offres publiées"
              value={indicators.published_job_offers}
              detail="Offres de la plateforme pendant la période"
            />
            <MetricCard
              label="Candidatures"
              value={indicators.applications_total}
              detail="Tous les statuts confondus"
            />
            <MetricCard
              label="Taux d’embauche déclaré"
              value={
                indicators.hire_rate_percent === null
                  ? "—"
                  : `${indicators.hire_rate_percent.toLocaleString("fr-FR")} %`
              }
              detail={`${indicators.hired_applications} embauches sur ${indicators.closed_applications} candidatures clôturées`}
            />
            <MetricCard
              label="Organisations"
              value={indicators.organisations}
              detail="Organisations enregistrées pendant la période"
            />
            <MetricCard
              label="Formations publiées"
              value={indicators.published_courses}
              detail="Catalogue visible aux candidats"
            />
            <MetricCard
              label="Inscriptions actives"
              value={indicators.active_enrollments}
              detail="Inscriptions non clôturées"
            />
            <MetricCard
              label="Formations terminées"
              value={indicators.course_completions}
              detail="Achèvements enregistrés pendant la période"
            />
          </div>

          <div className="market-charts">
            <ChartFrame
              title="État des candidatures"
              description="Répartition des candidatures par statut. Les recrutements sont comptés uniquement après déclaration par l’employeur."
            >
              <div className="market-bars">
                {indicators.applications_by_status.length ? (
                  indicators.applications_by_status.map((item) => (
                    <div className="market-bar" key={item.status}>
                      <div className="market-bar__label">
                        <span>{applicationStatusLabels[item.status]}</span>
                        <strong>{item.count}</strong>
                      </div>
                      <div className="market-bar__track">
                        <span style={{ width: `${(item.count / maxStatusCount) * 100}%` }} />
                      </div>
                    </div>
                  ))
                ) : (
                  <p className="market-empty">Aucune candidature pour cette période.</p>
                )}
              </div>
            </ChartFrame>
            <ChartFrame
              title="Compétences les plus demandées"
              description="Nombre d’offres publiées pendant la période qui demandent chaque compétence."
            >
              <div className="market-bars">
                {indicators.top_skills.length ? (
                  indicators.top_skills.map((item) => (
                    <div className="market-bar" key={item.skill}>
                      <div className="market-bar__label">
                        <span>{item.skill}</span>
                        <strong>{item.offer_count}</strong>
                      </div>
                      <div className="market-bar__track">
                        <span style={{ width: `${(item.offer_count / maxSkillCount) * 100}%` }} />
                      </div>
                    </div>
                  ))
                ) : (
                  <p className="market-empty">Aucune compétence déclarée dans les offres.</p>
                )}
              </div>
            </ChartFrame>
          </div>
          <div className="market-charts">
            <DataTable
              caption="Candidatures par statut"
              rows={indicators.applications_by_status}
              getRowId={(row) => row.status}
              emptyMessage="Aucune candidature pour cette période."
              columns={[
                { id: "status", header: "Statut", cell: (row) => applicationStatusLabels[row.status] },
                { id: "count", header: "Nombre", cell: (row) => row.count },
              ]}
            />
            <DataTable
              caption="Offres par compétence demandée"
              rows={indicators.top_skills}
              getRowId={(row) => row.skill}
              emptyMessage="Aucune compétence déclarée dans les offres."
              columns={[
                { id: "skill", header: "Compétence", cell: (row) => row.skill },
                { id: "offers", header: "Nombre d’offres", cell: (row) => row.offer_count },
              ]}
            />
          </div>
          <p className="market-footnote">
            Le taux d’embauche est calculé comme les candidatures marquées « recrutée » divisées
            par les candidatures clôturées (« recrutée » ou « non retenue »). C’est un résultat
            déclaré, pas une mesure indépendante de l’insertion professionnelle.
          </p>
        </>
      )}
    </section>
  );
}

type CourseFormValues = {
  title: string;
  summary: string;
  skills: string;
  delivery_mode: CourseDeliveryMode;
  location: string;
  governorate_code: string;
  municipality_code: string;
  street_address: string;
  starts_on: string;
  ends_on: string;
  duration_hours: string;
  capacity: string;
  price_tnd: string;
  status: TrainingCourseDraft["status"];
};

const emptyCourseForm: CourseFormValues = {
  title: "",
  summary: "",
  skills: "",
  delivery_mode: "online",
  location: "",
  governorate_code: "",
  municipality_code: "",
  street_address: "",
  starts_on: "",
  ends_on: "",
  duration_hours: "1",
  capacity: "20",
  price_tnd: "",
  status: "draft",
};

function courseDraft(values: CourseFormValues): TrainingCourseDraft {
  return {
    title: values.title.trim(),
    summary: values.summary.trim(),
    skills: values.skills.split(/[,\n]/).map((skill) => skill.trim()).filter(Boolean),
    delivery_mode: values.delivery_mode,
    location: values.location.trim() || null,
    governorate_code: values.governorate_code || null,
    municipality_code: values.municipality_code || null,
    street_address: values.street_address.trim() || null,
    starts_on: values.starts_on || null,
    ends_on: values.ends_on || null,
    duration_hours: Number(values.duration_hours),
    capacity: Number(values.capacity),
    price_tnd: values.price_tnd.trim() || null,
    status: values.status,
  };
}

function valuesFromCourse(course: TrainingCourse): CourseFormValues {
  return {
    title: course.title,
    summary: course.summary,
    skills: course.skills.join(", "),
    delivery_mode: course.delivery_mode,
    location: course.location ?? "",
    governorate_code: course.governorate_code ?? "",
    municipality_code: course.municipality_code ?? "",
    street_address: course.street_address ?? "",
    starts_on: course.starts_on ?? "",
    ends_on: course.ends_on ?? "",
    duration_hours: String(course.duration_hours),
    capacity: String(course.capacity),
    price_tnd: course.price_tnd ?? "",
    status: course.status,
  };
}

export function TrainingProviderDashboardPage({ token }: { token: string }) {
  const [courses, setCourses] = useState<TrainingCourse[]>([]);
  const [form, setForm] = useState<CourseFormValues>(emptyCourseForm);
  const [editingCourseId, setEditingCourseId] = useState<string | null>(null);
  const [selectedCourseId, setSelectedCourseId] = useState("");
  const [enrollments, setEnrollments] = useState<ProviderCourseEnrollment[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  async function loadCourses() {
    const results = await fetchTrainingCourses(token);
    setCourses(results);
    if (!selectedCourseId && results.length) setSelectedCourseId(results[0].id);
  }

  async function loadEnrollments(courseId: string) {
    setEnrollments(await fetchProviderCourseEnrollments(token, courseId));
  }

  useEffect(() => {
    let cancelled = false;
    fetchTrainingCourses(token)
      .then((results) => {
        if (!cancelled) {
          setCourses(results);
          setSelectedCourseId((current) => current || results[0]?.id || "");
        }
      })
      .catch((cause: unknown) => {
        if (!cancelled) setError(errorMessage(cause));
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [token]);

  useEffect(() => {
    if (!selectedCourseId) {
      setEnrollments([]);
      return;
    }
    let cancelled = false;
    fetchProviderCourseEnrollments(token, selectedCourseId)
      .then((results) => {
        if (!cancelled) setEnrollments(results);
      })
      .catch((cause: unknown) => {
        if (!cancelled) setError(errorMessage(cause));
      });
    return () => {
      cancelled = true;
    };
  }, [token, selectedCourseId]);

  async function saveCourse(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSaving(true);
    setError("");
    setNotice("");
    try {
      const payload = courseDraft(form);
      const saved = editingCourseId
        ? await updateTrainingCourse(token, editingCourseId, payload)
        : await createTrainingCourse(token, payload);
      await loadCourses();
      setSelectedCourseId(saved.id);
      setEditingCourseId(null);
      setForm(emptyCourseForm);
      setNotice(editingCourseId ? "La formation a été mise à jour." : "La formation a été créée.");
    } catch (cause: unknown) {
      setError(errorMessage(cause));
    } finally {
      setIsSaving(false);
    }
  }

  function editCourse(course: TrainingCourse) {
    setEditingCourseId(course.id);
    setSelectedCourseId(course.id);
    setForm(valuesFromCourse(course));
    setNotice("");
    setError("");
  }

  async function updateEnrollment(
    enrollmentId: string,
    nextStatus: CourseEnrollmentStatus,
  ) {
    setError("");
    try {
      await updateCourseEnrollmentStatus(token, enrollmentId, nextStatus);
      await Promise.all([loadCourses(), loadEnrollments(selectedCourseId)]);
    } catch (cause: unknown) {
      setError(errorMessage(cause));
    }
  }

  const activeEnrollments = courses.reduce((total, course) => total + course.enrollment_count, 0);
  const completions = courses.reduce((total, course) => total + course.completed_count, 0);

  return (
    <section className="market-page">
      <div className="eyebrow">ORGANISME DE FORMATION</div>
      <h1>Votre catalogue de formations</h1>
      <p className="market-page__intro">
        Publiez des formations reliées aux compétences et suivez les inscriptions ainsi que les
        achèvements de vos cours.
      </p>
      <div className="market-metrics market-metrics--three">
        <MetricCard label="Formations" value={courses.length} detail="Brouillons, publiées et archivées" />
        <MetricCard label="Inscriptions actives" value={activeEnrollments} detail="Participants actuellement inscrits" />
        <MetricCard label="Achèvements" value={completions} detail="Formations marquées terminées" />
      </div>

      <Card className="market-panel">
        <div className="market-panel__heading">
          <div>
            <h2>{editingCourseId ? "Modifier la formation" : "Créer une formation"}</h2>
            <p>Les cours en brouillon ne sont pas visibles des candidats.</p>
          </div>
          {editingCourseId && (
            <Button
              variant="secondary"
              onClick={() => {
                setEditingCourseId(null);
                setForm(emptyCourseForm);
              }}
            >
              Annuler la modification
            </Button>
          )}
        </div>
        <form className="workspace-form market-course-form" onSubmit={(event) => void saveCourse(event)}>
          <label className="form-field market-field--wide">
            <span className="form-field__label">Titre</span>
            <input className="input" required minLength={2} maxLength={160} value={form.title}
              onChange={(event) => setForm({ ...form, title: event.target.value })} />
          </label>
          <label className="form-field market-field--wide">
            <span className="form-field__label">Résumé</span>
            <textarea className="input workspace-textarea" required minLength={10} maxLength={5000}
              value={form.summary} onChange={(event) => setForm({ ...form, summary: event.target.value })} />
          </label>
          <label className="form-field market-field--wide">
            <span className="form-field__label">Compétences enseignées</span>
            <input className="input" required placeholder="Ex. Excel, analyse de données"
              value={form.skills} onChange={(event) => setForm({ ...form, skills: event.target.value })} />
            <span className="form-field__hint">Séparez les compétences par une virgule.</span>
          </label>
          <label className="form-field">
            <span className="form-field__label">Mode</span>
            <select className="select" value={form.delivery_mode}
              onChange={(event) => setForm({ ...form, delivery_mode: event.target.value as CourseDeliveryMode })}>
              <option value="online">À distance</option>
              <option value="in_person">En présentiel</option>
              <option value="hybrid">Hybride</option>
            </select>
          </label>
          <LocationSelect
            governorateRequired={form.delivery_mode !== "online"}
            governorateCode={form.governorate_code}
            municipalityCode={form.municipality_code}
            streetAddress={form.street_address}
            onChange={({ governorateCode, municipalityCode, streetAddress }) =>
              setForm({ ...form, governorate_code: governorateCode, municipality_code: municipalityCode, street_address: streetAddress, location: streetAddress })
            }
          />
          <label className="form-field">
            <span className="form-field__label">Date de début</span>
            <input className="input" type="date" value={form.starts_on}
              onChange={(event) => setForm({ ...form, starts_on: event.target.value })} />
          </label>
          <label className="form-field">
            <span className="form-field__label">Date de fin</span>
            <input className="input" type="date" min={form.starts_on || undefined} value={form.ends_on}
              onChange={(event) => setForm({ ...form, ends_on: event.target.value })} />
          </label>
          <label className="form-field">
            <span className="form-field__label">Durée (heures)</span>
            <input className="input" type="number" min={1} max={2000} required value={form.duration_hours}
              onChange={(event) => setForm({ ...form, duration_hours: event.target.value })} />
          </label>
          <label className="form-field">
            <span className="form-field__label">Capacité</span>
            <input className="input" type="number" min={1} max={10000} required value={form.capacity}
              onChange={(event) => setForm({ ...form, capacity: event.target.value })} />
          </label>
          <label className="form-field">
            <span className="form-field__label">Prix (TND, facultatif)</span>
            <input className="input" type="number" min={0} step="0.01" value={form.price_tnd}
              onChange={(event) => setForm({ ...form, price_tnd: event.target.value })} />
          </label>
          <label className="form-field">
            <span className="form-field__label">Statut</span>
            <select className="select" value={form.status}
              onChange={(event) => setForm({ ...form, status: event.target.value as TrainingCourseDraft["status"] })}>
              <option value="draft">Brouillon</option>
              <option value="published">Publiée</option>
              <option value="archived">Archivée</option>
            </select>
          </label>
          {error && <p className="workspace-error market-field--wide" role="alert">{error}</p>}
          {notice && <p className="workspace-success market-field--wide" role="status">{notice}</p>}
          <div className="market-field--wide">
            <Button type="submit" disabled={isSaving}>
              {isSaving ? "Enregistrement…" : editingCourseId ? "Enregistrer les changements" : "Créer la formation"}
            </Button>
          </div>
        </form>
      </Card>

      <div className="market-section-heading">
        <h2>Vos formations</h2>
        <Badge>{courses.length}</Badge>
      </div>
      {isLoading && <p aria-live="polite">Chargement des formations…</p>}
      {!isLoading && courses.length === 0 && (
        <Card className="market-panel">
          <EmptyState
            title="Aucune formation pour le moment"
            description="Créez un cours et publiez-le pour le rendre visible aux candidats."
          />
        </Card>
      )}
      <div className="market-course-grid">
        {courses.map((course) => (
          <Card className="market-course-card" key={course.id}>
            <div className="market-panel__heading">
              <div>
                <Badge tone={course.status === "published" ? "success" : "neutral"}>
                  {course.status === "published" ? "Publiée" : course.status === "draft" ? "Brouillon" : "Archivée"}
                </Badge>
                <h3>{course.title}</h3>
              </div>
              <Button variant="secondary" onClick={() => editCourse(course)}>Modifier</Button>
            </div>
            <p>{course.summary}</p>
            <ul className="market-course-meta">
              <li>{deliveryLabels[course.delivery_mode]}{course.location ? ` · ${course.location}` : ""}</li>
              <li>{formatDate(course.starts_on)} – {formatDate(course.ends_on)} · {course.duration_hours} h</li>
              <li>{course.enrollment_count} / {course.capacity} inscrits actifs · {course.completed_count} terminés</li>
              <li>{course.price_tnd === null ? "Prix non renseigné" : `${Number(course.price_tnd).toLocaleString("fr-FR")} TND`}</li>
              <li>Compétences : {course.skills.join(", ")}</li>
            </ul>
            <Button
              variant={selectedCourseId === course.id ? "primary" : "secondary"}
              onClick={() => setSelectedCourseId(course.id)}
            >
              {selectedCourseId === course.id ? "Liste sélectionnée" : "Voir les inscrits"}
            </Button>
          </Card>
        ))}
      </div>

      {selectedCourseId && (
        <Card className="market-panel" as="section">
          <div className="market-section-heading">
            <h2>Participants</h2>
            <Badge>{enrollments.length}</Badge>
          </div>
          {error && <p className="workspace-error" role="alert">{error}</p>}
          <DataTable<ProviderCourseEnrollment>
            caption="Participants inscrits à la formation sélectionnée"
            rows={enrollments}
            getRowId={(row) => row.id}
            emptyMessage="Aucune inscription pour cette formation."
            columns={[
              { id: "name", header: "Participant", cell: (row) => row.candidate_name || "Nom non renseigné" },
              { id: "location", header: "Lieu", cell: (row) => row.candidate_location || "Non renseigné" },
              { id: "skills", header: "Compétences", cell: (row) => row.candidate_skills.join(", ") || "Non renseignées" },
              { id: "status", header: "Statut", cell: (row) => enrollmentStatusLabels[row.status] },
              {
                id: "action",
                header: "Action",
                cell: (row) => row.status === "enrolled" ? (
                  <div className="market-row-actions">
                    <Button variant="secondary" onClick={() => void updateEnrollment(row.id, "completed")}>
                      Marquer terminée
                    </Button>
                    <Button variant="ghost" onClick={() => void updateEnrollment(row.id, "withdrawn")}>
                      Désinscrire
                    </Button>
                  </div>
                ) : "—",
              },
            ]}
          />
        </Card>
      )}
    </section>
  );
}

export function CandidateCoursesPage({ token }: { token: string }) {
  const [courses, setCourses] = useState<TrainingCourse[]>([]);
  const [enrollments, setEnrollments] = useState<CourseEnrollment[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [busyCourseId, setBusyCourseId] = useState("");

  async function refresh() {
    const [available, mine] = await Promise.all([
      fetchPublishedCourses(token),
      fetchCandidateEnrollments(token),
    ]);
    setCourses(available);
    setEnrollments(mine);
  }

  useEffect(() => {
    let cancelled = false;
    Promise.all([fetchPublishedCourses(token), fetchCandidateEnrollments(token)])
      .then(([available, mine]) => {
        if (!cancelled) {
          setCourses(available);
          setEnrollments(mine);
        }
      })
      .catch((cause: unknown) => {
        if (!cancelled) setError(errorMessage(cause));
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [token]);

  async function enroll(course: TrainingCourse) {
    setBusyCourseId(course.id);
    setError("");
    try {
      await enrollInCourse(token, course.id);
      await refresh();
    } catch (cause: unknown) {
      setError(errorMessage(cause));
    } finally {
      setBusyCourseId("");
    }
  }

  const enrollmentByCourse = new Map(enrollments.map((item) => [item.course_id, item]));

  return (
    <section className="market-page">
      <div className="eyebrow">APPRENDRE ET PROGRESSER</div>
      <h1>Formations disponibles</h1>
      <p className="market-page__intro">Consultez les informations des organismes et inscrivez-vous aux cours publiés.</p>
      {error && <p className="workspace-error" role="alert">{error}</p>}
      {isLoading && <p aria-live="polite">Chargement du catalogue…</p>}
      {!isLoading && courses.length === 0 && (
        <Card className="market-panel">
          <EmptyState
            title="Aucune formation publiée pour le moment"
            description="Les formations apparaîtront ici lorsqu’un organisme les publiera."
          />
        </Card>
      )}
      <div className="market-course-grid">
        {courses.map((course) => {
          const enrollment = enrollmentByCourse.get(course.id);
          const isFull = course.enrollment_count >= course.capacity;
          return (
            <Card className="market-course-card" key={course.id}>
              <div className="market-panel__heading">
                <div>
                  <Badge tone="accent">{deliveryLabels[course.delivery_mode]}</Badge>
                  <h2>{course.title}</h2>
                </div>
                <Badge>{course.price_tnd === null ? "Prix à confirmer" : `${Number(course.price_tnd).toLocaleString("fr-FR")} TND`}</Badge>
              </div>
              <p>{course.summary}</p>
              <ul className="market-course-meta">
                <li>{course.location || "À distance"} · {formatDate(course.starts_on)} – {formatDate(course.ends_on)}</li>
                <li>{course.duration_hours} heures · {course.enrollment_count} / {course.capacity} places occupées</li>
                <li>Compétences : {course.skills.join(", ")}</li>
              </ul>
              <Button
                disabled={Boolean(enrollment) || isFull || busyCourseId === course.id}
                onClick={() => void enroll(course)}
              >
                {busyCourseId === course.id
                  ? "Inscription…"
                  : enrollment
                    ? enrollmentStatusLabels[enrollment.status]
                    : isFull
                      ? "Complet"
                      : "M’inscrire"}
              </Button>
            </Card>
          );
        })}
      </div>
    </section>
  );
}

export function CandidateApplicationsPage({ token }: { token: string }) {
  const [applications, setApplications] = useState<JobApplication[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [busyId, setBusyId] = useState("");
  const [decisions, setDecisions] = useState<JobOfferDecision[]>([]);

  useEffect(() => {
    let cancelled = false;
    Promise.all([fetchCandidateApplications(token), fetchCandidateOfferDecisions(token)])
      .then(([results, offers]) => {
        if (!cancelled) { setApplications(Array.isArray(results) ? results : []); setDecisions(Array.isArray(offers) ? offers : []); }
      })
      .catch((cause: unknown) => {
        if (!cancelled) setError(errorMessage(cause));
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [token]);

  async function withdraw(application: JobApplication) {
    setBusyId(application.id);
    setError("");
    try {
      const updated = await withdrawCandidateApplication(token, application.id);
      setApplications((current) => current.map((item) => item.id === updated.id ? updated : item));
    } catch (cause: unknown) {
      setError(errorMessage(cause));
    } finally {
      setBusyId("");
    }
  }

  async function respond(decision: JobOfferDecision, status: "accepted" | "declined") {
    setBusyId(decision.id);
    try { const updated = await respondToJobOffer(token, decision.id, status); setDecisions((all) => all.map((item) => item.id === updated.id ? updated : item)); if (status === "accepted") setApplications((all) => all.map((item) => item.id === decision.application_id ? { ...item, status: "hired" } : item)); }
    catch (cause: unknown) { setError(errorMessage(cause)); }
    finally { setBusyId(""); }
  }

  return (
    <section className="market-page">
      <div className="eyebrow">SUIVI PERSONNEL</div>
      <h1>Mes candidatures</h1>
      <p className="market-page__intro">Consultez l’état des candidatures que vous avez envoyées.</p>
      {error && <p className="workspace-error" role="alert">{error}</p>}
      {isLoading && <p aria-live="polite">Chargement des candidatures…</p>}
      {!isLoading && applications.length === 0 && (
        <Card className="market-panel">
          <EmptyState title="Aucune candidature" description="Vos candidatures envoyées apparaîtront ici." />
        </Card>
      )}
      <div className="market-list">
        {applications.map((application) => (
          <Card className="market-list-card" key={application.id}>
            <div>
              <h2>{application.job_title}</h2>
              <p>{application.location} · Envoyée le {formatDate(application.created_at)}</p>
            </div>
            <Badge tone={application.status === "hired" ? "success" : "neutral"}>
              {applicationStatusLabels[application.status]}
            </Badge>
            {decisions.filter((decision) => decision.application_id === application.id && decision.status === "pending").map((decision) => <div className="market-section-heading" key={decision.id}><p>Offre formelle reçue{decision.response_deadline ? ` · réponse avant le ${new Date(decision.response_deadline).toLocaleDateString("fr-FR")}` : ""}</p><Button disabled={busyId === decision.id} onClick={() => void respond(decision, "accepted")}>Accepter</Button><Button variant="secondary" disabled={busyId === decision.id} onClick={() => void respond(decision, "declined")}>Décliner</Button></div>)}
            {!(["hired", "rejected", "withdrawn"] as JobApplicationStatus[]).includes(application.status) && (
              <Button variant="ghost" disabled={busyId === application.id} onClick={() => void withdraw(application)}>
                {busyId === application.id ? "Retrait…" : "Retirer ma candidature"}
              </Button>
            )}
          </Card>
        ))}
      </div>
    </section>
  );
}

export function EmployerApplicationsPage({ token, onNavigate }: { token: string; onNavigate: (page: string) => void }) {
  const [applications, setApplications] = useState<EmployerApplication[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [busyId, setBusyId] = useState("");
  const [detail, setDetail] = useState<EmployerApplicationDetail | null>(null);
  const [notes, setNotes] = useState<ApplicationNote[]>([]);
  const [evaluation, setEvaluation] = useState<ApplicationEvaluation | null>(null);
  const [noteDraft, setNoteDraft] = useState("");
  const [offerTerms, setOfferTerms] = useState("");

  useEffect(() => {
    let cancelled = false;
    fetchEmployerApplications(token)
      .then((results) => {
        if (!cancelled) setApplications(results);
      })
      .catch((cause: unknown) => {
        if (!cancelled) setError(errorMessage(cause));
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [token]);

  async function updateStatus(
    application: EmployerApplication,
    nextStatus: Exclude<JobApplicationStatus, "submitted">,
  ) {
    setBusyId(application.id);
    setError("");
    try {
      const updated = await updateEmployerApplicationStatus(token, application.id, nextStatus);
      setApplications((current) =>
        current.map((item) => item.id === updated.id ? { ...item, status: updated.status } : item),
      );
    } catch (cause: unknown) {
      setError(errorMessage(cause));
    } finally {
      setBusyId("");
    }
  }

  async function openDetail(applicationId: string) {
    if (detail?.id === applicationId) { setDetail(null); return; }
    try {
      const [applicationDetail, applicationNotes, applicationEvaluation] = await Promise.all([
        fetchEmployerApplicationDetail(token, applicationId), fetchApplicationNotes(token, applicationId), fetchApplicationEvaluation(token, applicationId),
      ]);
      setDetail(applicationDetail); setNotes(applicationNotes); setEvaluation(applicationEvaluation);
    } catch (cause: unknown) { setError(errorMessage(cause)); }
  }

  return (
    <section className="market-page">
      <div className="eyebrow">RECRUTEMENT</div>
      <h1>Candidatures reçues</h1>
      <p className="market-page__intro">
        Consultez les candidatures liées à vos offres et enregistrez une décision explicite pour
        suivre les résultats.
      </p>
      {error && <p className="workspace-error" role="alert">{error}</p>}
      {isLoading && <p aria-live="polite">Chargement des candidatures…</p>}
      {!isLoading && applications.length === 0 && (
        <Card className="market-panel">
          <EmptyState title="Aucune candidature reçue" description="Les candidatures envoyées à vos offres apparaîtront ici." />
        </Card>
      )}
      <div className="market-list">
        {applications.map((application) => {
          const closed = ["hired", "rejected", "withdrawn"].includes(application.status);
          return (
            <Card className="market-applicant-card" key={application.id}>
              <div className="market-panel__heading">
                <div>
                  <Badge tone={application.status === "hired" ? "success" : "neutral"}>
                    {applicationStatusLabels[application.status]}
                  </Badge>
                  <h2>{application.candidate_name || "Candidat sans nom renseigné"}</h2>
                  <p>{application.job_title} · {application.candidate_location || "Lieu non renseigné"}</p>
                </div>
                {!closed && (
                  <label className="form-field market-status-control">
                    <span className="form-field__label">Mettre à jour le statut</span>
                    <select
                      className="select"
                      aria-label={`Statut de la candidature de ${application.candidate_name || "ce candidat"}`}
                      value={application.status}
                      disabled={busyId === application.id}
                      onChange={(event) =>
                        void updateStatus(
                          application,
                          event.target.value as Exclude<JobApplicationStatus, "submitted">,
                        )
                      }
                    >
                      <option value={application.status}>{applicationStatusLabels[application.status]}</option>
                      {employerApplicationNextStatuses[application.status].map((nextStatus) => (
                        <option value={nextStatus} key={nextStatus}>{applicationStatusLabels[nextStatus]}</option>
                      ))}
                    </select>
                  </label>
                )}
              </div>
              <p className="market-applicant-skills">
                Compétences du profil : {application.candidate_skills.length
                  ? application.candidate_skills.join(", ")
                  : "Non renseignées"}
              </p>
              <Button variant="ghost" onClick={() => void openDetail(application.id)}>{detail?.id === application.id ? "Masquer les détails" : "Détails, notes et évaluation"}</Button>
              {detail?.id === application.id && <section className="market-panel"><h3>Parcours déclaré</h3><p>{detail.experience_entries.length} expérience(s) · {detail.education_entries.length} formation(s)</p><Button variant="secondary" onClick={() => void ensureApplicationConversation(token, application.id).then((conversation) => { sessionStorage.setItem("mahara-match-active-conversation", conversation.id); onNavigate("Messages"); }).catch((cause: unknown) => setError(errorMessage(cause)))}>Ouvrir une conversation</Button>{application.status === "offer_made" && <form className="workspace-form" onSubmit={(event) => { event.preventDefault(); void createFormalOffer(token, application.id, { response_deadline: null, proposed_conditions: { summary: offerTerms } }).then(() => setOfferTerms("" )).catch((cause: unknown) => setError(errorMessage(cause))); }}><label className="form-field"><span className="form-field__label">Conditions de l’offre formelle</span><textarea className="input workspace-textarea" required minLength={10} value={offerTerms} onChange={(event) => setOfferTerms(event.target.value)}/></label><Button type="submit">Envoyer l’offre formelle</Button></form>}<h3>Notes privées</h3>{notes.map((note) => <p key={note.id}>{note.content}</p>)}<form className="workspace-form" onSubmit={(event) => { event.preventDefault(); void addApplicationNote(token, application.id, noteDraft).then((note) => { setNotes((all) => [...all, note]); setNoteDraft(""); }).catch((cause: unknown) => setError(errorMessage(cause))); }}><label className="form-field"><span className="form-field__label">Ajouter une note privée</span><textarea className="input workspace-textarea" required value={noteDraft} onChange={(event) => setNoteDraft(event.target.value)}/></label><Button type="submit">Enregistrer la note</Button></form><h3>Évaluation structurée</h3><label className="form-field"><span className="form-field__label">Points forts</span><textarea className="input workspace-textarea" value={evaluation?.strengths ?? ""} onChange={(event) => setEvaluation({ id: evaluation?.id ?? "", criteria: evaluation?.criteria ?? [], strengths: event.target.value, concerns: evaluation?.concerns ?? null, updated_at: "" })}/></label><label className="form-field"><span className="form-field__label">Points à approfondir</span><textarea className="input workspace-textarea" value={evaluation?.concerns ?? ""} onChange={(event) => setEvaluation({ id: evaluation?.id ?? "", criteria: evaluation?.criteria ?? [], strengths: evaluation?.strengths ?? null, concerns: event.target.value, updated_at: "" })}/></label><Button variant="secondary" onClick={() => void saveApplicationEvaluation(token, application.id, { criteria: evaluation?.criteria ?? [], strengths: evaluation?.strengths ?? null, concerns: evaluation?.concerns ?? null }).then(setEvaluation).catch((cause: unknown) => setError(errorMessage(cause)))}>Enregistrer l’évaluation</Button></section>}
              {closed && <p className="market-footnote">Décision clôturée et enregistrée.</p>}
            </Card>
          );
        })}
      </div>
    </section>
  );
}

export function EmployerDashboardPage({ token, onNavigate }: { token: string; onNavigate: (page: string) => void }) {
  const [offers, setOffers] = useState<import("./auth").JobOffer[]>([]);
  const [applications, setApplications] = useState<EmployerApplication[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  useEffect(() => {
    let cancelled = false;
    Promise.all([fetchEmployerOffers(token), fetchEmployerApplications(token)])
      .then(([offerRows, applicationRows]) => { if (!cancelled) { setOffers(Array.isArray(offerRows) ? offerRows : []); setApplications(Array.isArray(applicationRows) ? applicationRows : []); } })
      .catch((cause: unknown) => { if (!cancelled) setError(errorMessage(cause)); })
      .finally(() => { if (!cancelled) setIsLoading(false); });
    return () => { cancelled = true; };
  }, [token]);
  const newApplications = applications.filter((item) => item.status === "submitted");
  const inReview = applications.filter((item) => item.status === "reviewing").length;
  const interviews = applications.filter((item) => item.status === "interview").length;
  const hired = applications.filter((item) => item.status === "hired").length;
  const publishedOffers = offers.filter((offer) => offer.status === "published").length;
  const draftOffers = offers.filter((offer) => offer.status === "draft").length;
  const recentApplications = [...applications]
    .sort((left, right) => Date.parse(right.created_at) - Date.parse(left.created_at))
    .slice(0, 5);
  return <section className="market-page">
    <div className="eyebrow">VUE D’ENSEMBLE</div><h1>Votre espace employeur</h1>
    <p className="market-page__intro">Retrouvez vos recrutements, les candidatures à examiner et les prochaines étapes.</p>
    <Card className="employer-create-cta"><span className="overview-icon overview-icon--blue"><BriefcaseBusiness size={22}/></span><div><p className="eyebrow">RECRUTEMENT</p><h2>Publiez une offre pour trouver les bons profils</h2><p>Décrivez le poste et ses compétences clés pour la proposer aux candidats.</p></div><Button onClick={() => onNavigate("Mes offres")}>Créer une offre <ArrowUpRight size={16}/></Button></Card>
    {error && <p className="workspace-error" role="alert">{error}</p>}
    {isLoading ? <p aria-live="polite">Chargement de votre activité…</p> : <>
      <div className="market-metrics employer-dashboard-metrics">
        <MetricCard label="Offres actives" value={publishedOffers} detail="Offres actuellement publiées"/>
        <MetricCard label="Brouillons" value={draftOffers} detail="Offres enregistrées avant publication"/>
        <MetricCard label="À examiner" value={newApplications.length} detail="Nouvelles candidatures reçues"/>
        <MetricCard label="En cours d’examen" value={inReview} detail="Candidatures à l’étude"/>
        <MetricCard label="Entretiens" value={interviews} detail="Candidatures au stade entretien"/>
        <MetricCard label="Candidatures" value={applications.length} detail="Toutes les candidatures reçues"/>
        <MetricCard label="Recrutements déclarés" value={hired} detail="Résultats déclarés par votre organisation"/>
      </div>
      <Card className="market-panel employer-dashboard-attention">
        <div className="market-section-heading"><div><h2>À traiter en priorité</h2><p>Les candidatures reçues attendent une première décision.</p></div><Badge>{newApplications.length}</Badge></div>
        {newApplications.length ? <Button variant="secondary" onClick={() => onNavigate("Candidatures")}>Examiner les candidatures <ArrowUpRight size={16}/></Button> : <p className="market-footnote">Aucune nouvelle candidature à examiner.</p>}
      </Card>
      <Card className="market-panel"><div className="market-section-heading"><div><h2>Offres récentes</h2><p>Suivez les candidatures liées à vos offres.</p></div><Badge>{offers.length}</Badge></div>
        {offers.length ? <div className="market-list">{offers.map((offer) => { const count = applications.filter((item) => item.job_offer_id === offer.id).length; const offerStatus = offer.status ?? "published"; return <article className="market-org-offer" key={offer.id}><div><h3>{offer.title}</h3><p>{offer.location} · {offer.published_at ? `Publiée le ${formatDate(offer.published_at)}` : `Créée le ${formatDate(offer.created_at)}`}</p></div><div className="employer-dashboard-offer-badges"><Badge>{count} candidature{count === 1 ? "" : "s"}</Badge><Badge>{jobOfferStatusLabels[offerStatus]}</Badge></div></article>; })}</div> : <EmptyState title="Aucune offre enregistrée" description="Créez votre première offre pour commencer à suivre votre recrutement."/>}
      </Card>
      <Card className="market-panel">
        <div className="market-section-heading"><div><h2>Candidatures récentes</h2><p>Classées par date de réception.</p></div><Button variant="secondary" onClick={() => onNavigate("Candidatures")}>Tout voir</Button></div>
        {recentApplications.length ? <div className="market-list">{recentApplications.map((application) => <article className="market-org-offer" key={application.id}><div><h3>{application.candidate_name || "Candidat sans nom renseigné"}</h3><p>{application.job_title} · Reçue le {formatDate(application.created_at)}</p></div><Badge tone={application.status === "hired" ? "success" : "neutral"}>{applicationStatusLabels[application.status]}</Badge></article>)}</div> : <EmptyState title="Aucune candidature reçue" description="Les candidatures à vos offres apparaîtront ici."/>}
      </Card>
    </>}
  </section>;
}

export function EmployerOrganisationPage({ token }: { token: string }) {
  const [profile, setProfile] = useState<OrganisationProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [creating, setCreating] = useState(false);
  const [verification, setVerification] = useState("");
  const [evidenceUrl, setEvidenceUrl] = useState("");
  const [verificationStatus, setVerificationStatus] = useState("");
  useEffect(() => { let cancelled = false; fetchEmployerOrganisation(token).then((value) => { if (!cancelled) setProfile(value); }).catch((cause: unknown) => { if (!cancelled) { if (cause instanceof ApiError && cause.status === 404) { setCreating(true); setProfile({ id: "", organisation_type: "employer", name: "", website: null, sector: null, size: null, description: null, phone: null, contact_email: null, location: null, profile_details: {} }); } else setError(errorMessage(cause)); } }).finally(() => { if (!cancelled) setLoading(false); }); return () => { cancelled = true; }; }, [token]);
  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!profile) return; setSaving(true); setError(""); setNotice("");
    try { setProfile(creating ? await createEmployerOrganisation(token, profile) : await updateEmployerOrganisation(token, profile)); setCreating(false); setNotice("Les informations de votre organisation ont été enregistrées."); }
    catch (cause: unknown) { setError(errorMessage(cause)); } finally { setSaving(false); }
  }
  async function submitVerification(event: FormEvent<HTMLFormElement>) { event.preventDefault(); setError(""); try { const result = await submitOrganisationVerification(token, { supporting_information: verification, evidence_url: evidenceUrl || null }); setVerificationStatus(result.status); setNotice("Demande de vérification envoyée."); } catch (cause: unknown) { setError(errorMessage(cause)); } }
  const details = profile?.profile_details ?? {};
  function setDetail(key: string, value: unknown) { if (profile) setProfile({ ...profile, profile_details: { ...profile.profile_details, [key]: value } }); }
  const detailField = (label: string, key: string, multiline = false) => <label className="form-field"><span className="form-field__label">{label}</span>{multiline ? <textarea className="input workspace-textarea" rows={3} value={String(details[key] ?? "")} onChange={(event) => setDetail(key, event.target.value)}/> : <input className="input" value={String(details[key] ?? "")} onChange={(event) => setDetail(key, event.target.value)}/>}</label>;
  if (loading) return <section className="market-page"><h1>Mon organisation</h1><p aria-live="polite">Chargement des informations de votre organisation…</p></section>;
  if (!profile) return <section className="market-page"><div className="eyebrow">ESPACE EMPLOYEUR</div><h1>Mon organisation</h1><Card className="market-panel"><EmptyState title="Organisation non reliée à votre compte" description="Votre espace employeur n’est pas encore associé à une organisation. Contactez l’administrateur de la plateforme pour terminer la configuration."/>{error && <p className="workspace-error" role="alert">{error}</p>}</Card></section>;
  return <section className="market-page"><div className="eyebrow">ESPACE EMPLOYEUR</div><h1>{creating ? "Créer mon organisation" : "Mon organisation"}</h1><p className="market-page__intro">Présentez votre entreprise et ses besoins pour donner à l’assistant de recrutement un contexte utile.</p>{error && <p className="workspace-error" role="alert">{error}</p>}
    {!creating && <Card className="market-panel"><div className="market-section-heading"><div><h2>Vérification de l’organisation</h2><p>Le statut de vérification est visible dans votre espace.</p></div><Badge>{verificationStatus || profile.verification_status || "non vérifiée"}</Badge></div><form className="workspace-form" onSubmit={(event) => void submitVerification(event)}><label className="form-field"><span className="form-field__label">Informations justificatives</span><textarea className="input workspace-textarea" rows={3} minLength={20} required value={verification} onChange={(event) => setVerification(event.target.value)}/></label><label className="form-field"><span className="form-field__label">Lien vers un justificatif (facultatif)</span><input className="input" type="url" value={evidenceUrl} onChange={(event) => setEvidenceUrl(event.target.value)}/></label><Button type="submit">Demander la vérification</Button></form></Card>}
    <form className="workspace-form" onSubmit={(event) => void save(event)}>
      <Card className="market-panel"><div className="market-section-heading"><div><h2>Informations de base</h2><p>Les informations principales de votre structure.</p></div><Badge>Entreprise</Badge></div>
        <label className="form-field"><span className="form-field__label">Nom de l’organisation</span><input className="input" required minLength={2} maxLength={200} value={profile.name} onChange={(event) => setProfile({ ...profile, name: event.target.value })}/></label>
        <label className="form-field"><span className="form-field__label">Secteur</span><input className="input" maxLength={120} value={profile.sector ?? ""} onChange={(event) => setProfile({ ...profile, sector: event.target.value || null })}/></label>
        <label className="form-field"><span className="form-field__label">Taille</span><input className="input" maxLength={80} value={profile.size ?? ""} onChange={(event) => setProfile({ ...profile, size: event.target.value || null })}/></label>
        <label className="form-field"><span className="form-field__label">Lieu</span><input className="input" maxLength={200} value={profile.location ?? ""} onChange={(event) => setProfile({ ...profile, location: event.target.value || null })}/></label>
        <label className="form-field"><span className="form-field__label">Site web</span><input className="input" type="url" placeholder="https://…" value={profile.website ?? ""} onChange={(event) => setProfile({ ...profile, website: event.target.value || null })}/></label>
        <label className="form-field"><span className="form-field__label">Téléphone de contact</span><input className="input" type="tel" maxLength={40} value={profile.phone ?? ""} onChange={(event) => setProfile({ ...profile, phone: event.target.value || null })}/></label>
        <label className="form-field"><span className="form-field__label">E-mail de contact</span><input className="input" type="email" maxLength={320} value={profile.contact_email ?? ""} onChange={(event) => setProfile({ ...profile, contact_email: event.target.value || null })}/></label>
        <label className="form-field organisation-form__wide"><span className="form-field__label">Description</span><textarea className="input workspace-textarea" rows={3} maxLength={3000} value={profile.description ?? ""} onChange={(event) => setProfile({ ...profile, description: event.target.value || null })}/></label>
        {detailField("Activités principales", "activities", true)}
      </Card>
      <Card className="market-panel"><h2>Identité et culture</h2>{detailField("Mission", "mission", true)}{detailField("Vision", "vision", true)}{detailField("Valeurs clés", "values")}{detailField("Culture d’entreprise", "culture", true)}{detailField("Environnement de travail", "working_environment", true)}</Card>
      <Card className="market-panel"><h2>Équipes et services</h2><RepeatableOrganisationEntries title="Produits et services" fields={[{ key: "name", label: "Nom" }, { key: "description", label: "Description" }, { key: "category", label: "Catégorie" }]} value={details.products_services} onChange={(value) => setDetail("products_services", value)}/><RepeatableOrganisationEntries title="Équipes et départements" fields={[{ key: "name", label: "Équipe ou département" }, { key: "responsibilities", label: "Responsabilités" }, { key: "roles", label: "Rôles clés" }]} value={details.teams} onChange={(value) => setDetail("teams", value)}/></Card>
      <Card className="market-panel"><h2>Préférences de recrutement</h2>{detailField("Profils recherchés", "candidate_profiles", true)}{detailField("Compétences techniques importantes", "technical_skills")}{detailField("Qualités humaines", "soft_skills")}{detailField("Organisation du travail et langues", "work_preferences", true)}{detailField("Autres préférences", "other_preferences", true)}</Card>
      {notice && <p className="workspace-success" role="status">{notice}</p>}<Button type="submit" disabled={saving}>{saving ? "Enregistrement…" : "Enregistrer les informations"}</Button>
    </form></section>;
}

export function EmployerCandidatesPage({ token }: { token: string }) {
  const [query, setQuery] = useState(""); const [skill, setSkill] = useState(""); const [rows, setRows] = useState<CandidateDiscovery[]>([]); const [pools, setPools] = useState<TalentPool[]>([]); const [error, setError] = useState(""); const [busy, setBusy] = useState("");
  useEffect(() => { fetchTalentPools(token).then(setPools).catch((cause: unknown) => setError(errorMessage(cause))); }, [token]);
  async function search(event: FormEvent<HTMLFormElement>) { event.preventDefault(); setError(""); try { setRows(await searchEmployerCandidates(token, { q: query, skill })); } catch (cause: unknown) { setError(errorMessage(cause)); } }
  async function save(candidateId: string) { if (!pools[0]) { setError("Créez d’abord une liste de talents."); return; } setBusy(candidateId); try { await addCandidateToTalentPool(token, pools[0].id, candidateId); } catch (cause: unknown) { setError(errorMessage(cause)); } finally { setBusy(""); } }
  return <section className="market-page"><div className="eyebrow">RECRUTEMENT</div><h1>Découvrir des candidats</h1><p className="market-page__intro">Seuls les candidats ayant activé la visibilité employeur apparaissent ici.</p>{error && <p className="workspace-error" role="alert">{error}</p>}<Card className="market-panel"><form className="workspace-form" onSubmit={(event) => void search(event)}><label className="form-field"><span className="form-field__label">Nom, titre ou mot-clé</span><input className="input" value={query} onChange={(event) => setQuery(event.target.value)}/></label><label className="form-field"><span className="form-field__label">Compétence</span><input className="input" value={skill} onChange={(event) => setSkill(event.target.value)}/></label><Button type="submit"><Search size={16}/> Rechercher</Button></form></Card><div className="market-list">{rows.map((candidate) => <Card className="market-applicant-card" key={candidate.candidate_id}><div><h2>{candidate.professional_headline || "Profil candidat"}</h2><p>{candidate.location || "Lieu non renseigné"} · {candidate.skills.join(" · ")}</p>{candidate.matched_skills.length > 0 && <p>Compétences correspondantes : {candidate.matched_skills.join(", ")}</p>}</div><Button variant="secondary" disabled={busy === candidate.candidate_id} onClick={() => void save(candidate.candidate_id)}><UserPlus size={16}/> Ajouter à mes talents</Button></Card>)}</div>{!rows.length && <Card className="market-panel"><EmptyState title="Aucun résultat" description="Lancez une recherche pour consulter les profils visibles."/></Card>}</section>;
}

export function EmployerTalentPoolsPage({ token }: { token: string }) {
  const [pools, setPools] = useState<TalentPool[]>([]); const [active, setActive] = useState(""); const [members, setMembers] = useState<TalentPoolMember[]>([]); const [name, setName] = useState(""); const [error, setError] = useState("");
  useEffect(() => { fetchTalentPools(token).then((items) => { setPools(items); if (items[0]) setActive(items[0].id); }).catch((cause: unknown) => setError(errorMessage(cause))); }, [token]);
  useEffect(() => { if (active) fetchTalentPoolMembers(token, active).then(setMembers).catch((cause: unknown) => setError(errorMessage(cause))); }, [token, active]);
  async function create(event: FormEvent<HTMLFormElement>) { event.preventDefault(); try { const pool = await createTalentPool(token, name); setPools((current) => [...current, pool]); setActive(pool.id); setName(""); } catch (cause: unknown) { setError(errorMessage(cause)); } }
  return <section className="market-page"><div className="eyebrow">VIVIER DE TALENTS</div><h1>Talents sauvegardés</h1>{error && <p className="workspace-error" role="alert">{error}</p>}<Card className="market-panel"><form className="workspace-form" onSubmit={(event) => void create(event)}><label className="form-field"><span className="form-field__label">Nouvelle liste</span><input className="input" required value={name} onChange={(event) => setName(event.target.value)}/></label><Button type="submit">Créer une liste</Button></form><label className="form-field"><span className="form-field__label">Liste</span><select className="input" value={active} onChange={(event) => setActive(event.target.value)}>{pools.map((pool) => <option key={pool.id} value={pool.id}>{pool.name}</option>)}</select></label></Card><div className="market-list">{members.map((member) => <Card className="market-applicant-card" key={member.candidate_id}><div><h2>{member.professional_headline || "Profil candidat"}</h2><p>{member.location || "Lieu non renseigné"} · {member.skills.join(" · ")}</p>{member.private_note && <p>{member.private_note}</p>}</div><Button variant="ghost" onClick={() => void removeTalentPoolMember(token, active, member.candidate_id).then(() => setMembers((list) => list.filter((item) => item.candidate_id !== member.candidate_id))).catch((cause: unknown) => setError(errorMessage(cause)))}>Retirer</Button></Card>)}</div></section>;
}

export function EmployerMessagesPage({ token }: { token: string }) {
  const [conversations, setConversations] = useState<Conversation[]>([]); const [active, setActive] = useState(""); const [messages, setMessages] = useState<ConversationMessage[]>([]); const [draft, setDraft] = useState(""); const [error, setError] = useState("");
  useEffect(() => { fetchEmployerConversations(token).then((items) => { setConversations(items); const requested = sessionStorage.getItem("mahara-match-active-conversation"); setActive(requested && items.some((item) => item.id === requested) ? requested : items[0]?.id ?? ""); sessionStorage.removeItem("mahara-match-active-conversation"); }).catch((cause: unknown) => setError(errorMessage(cause))); }, [token]);
  useEffect(() => { if (active) fetchConversationMessages(token, active).then(setMessages).catch((cause: unknown) => setError(errorMessage(cause))); }, [token, active]);
  async function send(event: FormEvent<HTMLFormElement>) { event.preventDefault(); if (!active || !draft.trim()) return; try { const message = await sendConversationMessage(token, active, draft.trim()); setMessages((items) => [...items, message]); setDraft(""); } catch (cause: unknown) { setError(errorMessage(cause)); } }
  return <section className="market-page"><div className="eyebrow">ÉCHANGES</div><h1>Messages</h1>{error && <p className="workspace-error" role="alert">{error}</p>}<Card className="market-panel"><label className="form-field"><span className="form-field__label">Conversation</span><select className="input" value={active} onChange={(event) => setActive(event.target.value)}>{conversations.map((item) => <option value={item.id} key={item.id}>{item.candidate_name || "Candidat"} · {item.job_title}</option>)}</select></label><div className="market-list">{messages.map((message) => <article className="market-org-offer" key={message.id}><p>{message.content}</p><small>{new Date(message.created_at).toLocaleString("fr-FR")}</small></article>)}</div><form className="workspace-form" onSubmit={(event) => void send(event)}><label className="form-field"><span className="form-field__label">Votre message</span><textarea className="input workspace-textarea" required value={draft} onChange={(event) => setDraft(event.target.value)}/></label><Button type="submit" disabled={!active}>Envoyer</Button></form></Card></section>;
}

export function EmployerInterviewsPage({ token }: { token: string }) {
  const [items, setItems] = useState<EmployerInterview[]>([]); const [applications, setApplications] = useState<EmployerApplication[]>([]); const [error, setError] = useState(""); const [applicationId, setApplicationId] = useState(""); const [startsAt, setStartsAt] = useState(""); const [duration, setDuration] = useState(45); const [format, setFormat] = useState<"online" | "in_person">("online"); const [details, setDetails] = useState("");
  useEffect(() => { fetchEmployerInterviews(token).then(setItems).catch((cause: unknown) => setError(errorMessage(cause))); fetchEmployerApplications(token).then(setApplications).catch((cause: unknown) => setError(errorMessage(cause))); }, [token]);
  async function schedule(event: FormEvent<HTMLFormElement>) { event.preventDefault(); try { const created = await createEmployerInterview(token, { application_id: applicationId, starts_at: new Date(startsAt).toISOString(), duration_minutes: duration, format, meeting_details: details || null }); setItems((all) => [...all, created].sort((a, b) => Date.parse(a.starts_at) - Date.parse(b.starts_at))); setApplicationId(""); setStartsAt(""); setDetails(""); } catch (cause: unknown) { setError(errorMessage(cause)); } }
  return <section className="market-page"><div className="eyebrow">RECRUTEMENT</div><h1>Entretiens</h1><p className="market-page__intro">Planifiez des rendez-vous depuis les candidatures et suivez les confirmations.</p>{error && <p className="workspace-error" role="alert">{error}</p>}<Card className="market-panel"><h2>Planifier un entretien</h2><form className="workspace-form" onSubmit={(event) => void schedule(event)}><label className="form-field"><span className="form-field__label">Candidature</span><select className="input" required value={applicationId} onChange={(event) => setApplicationId(event.target.value)}><option value="">Choisir une candidature</option>{applications.filter((app) => !["hired", "rejected", "withdrawn"].includes(app.status)).map((app) => <option key={app.id} value={app.id}>{app.candidate_name || "Candidat"} · {app.job_title}</option>)}</select></label><label className="form-field"><span className="form-field__label">Date et heure</span><input className="input" type="datetime-local" required value={startsAt} onChange={(event) => setStartsAt(event.target.value)}/></label><label className="form-field"><span className="form-field__label">Durée (minutes)</span><input className="input" type="number" min={15} max={240} step={15} value={duration} onChange={(event) => setDuration(Number(event.target.value))}/></label><label className="form-field"><span className="form-field__label">Format</span><select className="input" value={format} onChange={(event) => setFormat(event.target.value as "online" | "in_person")}><option value="online">À distance</option><option value="in_person">En présentiel</option></select></label><label className="form-field"><span className="form-field__label">Lien ou lieu</span><input className="input" value={details} onChange={(event) => setDetails(event.target.value)}/></label><Button type="submit" disabled={!applicationId}>Planifier</Button></form></Card><div className="market-list">{items.map((item) => <Card className="market-applicant-card" key={item.id}><div><h2>{item.candidate_name || "Candidat"} · {item.job_title}</h2><p>{new Date(item.starts_at).toLocaleString("fr-FR")} · {item.duration_minutes} min · {item.format === "online" ? "À distance" : "En présentiel"}</p>{item.meeting_details && <p>{item.meeting_details}</p>}</div><Badge>{item.status}</Badge>{item.status === "confirmed" && <Button variant="ghost" onClick={() => void updateEmployerInterviewStatus(token, item.id, "completed").then((updated) => setItems((all) => all.map((old) => old.id === updated.id ? updated : old))).catch((cause: unknown) => setError(errorMessage(cause)))}>Marquer terminé</Button>}</Card>)}</div></section>;
}

export function CandidateInterviewsPage({ token }: { token: string }) {
  const [items, setItems] = useState<EmployerInterview[]>([]); const [error, setError] = useState("");
  useEffect(() => { fetchEmployerInterviews(token).then(setItems).catch((cause: unknown) => setError(errorMessage(cause))); }, [token]);
  async function respond(item: EmployerInterview, status: string) { try { const updated = await updateEmployerInterviewStatus(token, item.id, status); setItems((all) => all.map((row) => row.id === updated.id ? updated : row)); } catch (cause: unknown) { setError(errorMessage(cause)); } }
  return <section className="market-page"><div className="eyebrow">SUIVI PERSONNEL</div><h1>Mes entretiens</h1><p className="market-page__intro">Consultez les propositions d’entretien et confirmez votre disponibilité.</p>{error && <p className="workspace-error" role="alert">{error}</p>}{items.length ? <div className="market-list">{items.map((item) => <Card className="market-applicant-card" key={item.id}><div><h2>{item.job_title}</h2><p>{new Date(item.starts_at).toLocaleString("fr-FR")} · {item.duration_minutes} min · {item.format === "online" ? "À distance" : "En présentiel"}</p>{item.meeting_details && <p>{item.meeting_details}</p>}</div><Badge>{item.status}</Badge>{item.status === "proposed" && <Button onClick={() => void respond(item, "confirmed")}>Confirmer l’entretien</Button>}{["proposed", "confirmed"].includes(item.status) && <Button variant="ghost" onClick={() => void respond(item, "cancelled")}>Décliner</Button>}</Card>)}</div> : <Card className="market-panel"><EmptyState title="Aucun entretien proposé" description="Les entretiens proposés par les employeurs apparaîtront ici."/></Card>}</section>;
}

export function EmployerNotificationsPage({ token }: { token: string }) {
  const [items, setItems] = useState<EmployerNotification[]>([]); const [preferences, setPreferences] = useState<NotificationPreference[]>([]); const [error, setError] = useState("");
  useEffect(() => { fetchEmployerNotifications(token).then(setItems).catch((cause: unknown) => setError(errorMessage(cause))); fetchNotificationPreferences(token).then(setPreferences).catch((cause: unknown) => setError(errorMessage(cause))); }, [token]);
  return <section className="market-page"><div className="eyebrow">ACTIVITÉ</div><h1>Notifications</h1>{error && <p className="workspace-error" role="alert">{error}</p>}<Card className="market-panel"><h2>Préférences</h2>{preferences.map((pref) => <label className="candidate-discovery-consent" key={pref.notification_type}><input type="checkbox" checked={pref.enabled} onChange={(event) => void updateNotificationPreference(token, pref.notification_type, event.target.checked).then((updated) => setPreferences((all) => all.map((item) => item.notification_type === updated.notification_type ? updated : item))).catch((cause: unknown) => setError(errorMessage(cause)))}/>{pref.notification_type}</label>)}</Card><div className="market-list">{items.map((item) => <Card className="market-applicant-card" key={item.id}><div><h2>{item.title}</h2><p>{item.body}</p><small>{new Date(item.created_at).toLocaleString("fr-FR")}</small></div>{!item.read_at && <Button variant="ghost" onClick={() => void markEmployerNotificationRead(token, item.id).then((updated) => setItems((all) => all.map((row) => row.id === updated.id ? updated : row)))}>Marquer comme lue</Button>}</Card>)}</div></section>;
}

export function EmployerAnalyticsPage({ token }: { token: string }) {
  const [data, setData] = useState<EmployerAnalytics | null>(null); const [error, setError] = useState("");
  useEffect(() => { fetchEmployerAnalytics(token).then(setData).catch((cause: unknown) => setError(errorMessage(cause))); }, [token]);
  return <section className="market-page"><div className="eyebrow">INDICATEURS</div><h1>Statistiques de recrutement</h1>{error && <p className="workspace-error" role="alert">{error}</p>}{data && <><div className="market-metrics employer-dashboard-metrics"><MetricCard label="Candidatures" value={data.total_applications} detail="Toutes les candidatures"/><MetricCard label="Présélectionnées" value={data.shortlisted} detail="Au stade présélection"/><MetricCard label="Entretiens" value={data.interviews} detail="Entretiens engagés"/><MetricCard label="Recrutements" value={data.hires_reported} detail="Déclarés"/></div><Card className="market-panel"><h2>Résultats par offre</h2><div className="market-list">{data.applications_per_offer.map((offer) => <article className="market-org-offer" key={offer.job_offer_id}><h3>{offer.title}</h3><Badge>{offer.applications} candidature{offer.applications === 1 ? "" : "s"}</Badge></article>)}</div><p>Taux candidature vers entretien : {data.application_to_interview_percent ?? "—"}% · entretien vers recrutement : {data.interview_to_hire_percent ?? "—"}%</p>{!data.has_sufficient_data && <p className="market-footnote">Les indicateurs restent préliminaires avant cinq candidatures.</p>}</Card></>}</section>;
}

export function AdminOrganisationVerificationPage({ token }: { token: string }) {
  const [requests, setRequests] = useState<OrganisationVerification[]>([]); const [error, setError] = useState(""); const [busy, setBusy] = useState(""); const [notes, setNotes] = useState<Record<string, string>>({});
  useEffect(() => { fetchPendingOrganisationVerifications(token).then((items) => setRequests(Array.isArray(items) ? items : [])).catch((cause: unknown) => setError(errorMessage(cause))); }, [token]);
  async function review(item: OrganisationVerification, status: "verified" | "rejected") { setBusy(item.id); setError(""); try { await reviewOrganisationVerification(token, item.id, status, notes[item.id] ?? "Vérification effectuée selon les justificatifs fournis."); setRequests((all) => all.filter((row) => row.id !== item.id)); } catch (cause: unknown) { setError(errorMessage(cause)); } finally { setBusy(""); } }
  return <section className="market-page"><div className="eyebrow">ADMINISTRATION</div><h1>Vérification des organisations</h1><p className="market-page__intro">Examinez les justificatifs et enregistrez une décision avec une note de suivi.</p>{error && <p className="workspace-error" role="alert">{error}</p>}{requests.length === 0 ? <Card className="market-panel"><EmptyState title="Aucune demande en attente" description="Les demandes reçues apparaîtront ici."/></Card> : <div className="market-list">{requests.map((item) => <Card className="market-panel" key={item.id}><h2>{item.organisation_name || "Organisation"}</h2><p>{item.supporting_information}</p>{item.evidence_url && <p><a href={item.evidence_url} target="_blank" rel="noreferrer">Consulter le justificatif</a></p>}<label className="form-field"><span className="form-field__label">Note de décision (10 caractères minimum)</span><textarea className="input workspace-textarea" minLength={10} value={notes[item.id] ?? ""} onChange={(event) => setNotes((all) => ({ ...all, [item.id]: event.target.value }))}/></label><div className="market-section-heading"><Button disabled={busy === item.id || (notes[item.id] ?? "Vérification effectuée selon les justificatifs fournis.").trim().length < 10} onClick={() => void review(item, "verified")}>Vérifier</Button><Button variant="secondary" disabled={busy === item.id || (notes[item.id] ?? "").trim().length < 10} onClick={() => void review(item, "rejected")}>Rejeter</Button></div></Card>)}</div>}</section>;
}

function RepeatableOrganisationEntries({ title, fields, value, onChange }: { title: string; fields: { key: string; label: string }[]; value: unknown; onChange: (value: Record<string, string>[]) => void }) {
  const entries = Array.isArray(value) ? value as Record<string, string>[] : [];
  return <section className="organisation-entries"><h3>{title}</h3>{entries.map((entry, index) => <div className="organisation-entry" key={`${title}-${index}`}>
    {fields.map((field) => <label className="form-field" key={field.key}><span className="form-field__label">{field.label}</span>{field.key === "description" || field.key === "responsibilities" ? <textarea className="input workspace-textarea" rows={2} value={entry[field.key] ?? ""} onChange={(event) => onChange(entries.map((item, row) => row === index ? { ...item, [field.key]: event.target.value } : item))}/> : <input className="input" value={entry[field.key] ?? ""} onChange={(event) => onChange(entries.map((item, row) => row === index ? { ...item, [field.key]: event.target.value } : item))}/>}</label>)}
    <button className="button button--secondary" type="button" onClick={() => onChange(entries.filter((_, row) => row !== index))}>Supprimer</button>
  </div>)}<button className="button button--secondary" type="button" onClick={() => onChange([...entries, Object.fromEntries(fields.map((field) => [field.key, ""]))])}>Ajouter</button></section>;
}

