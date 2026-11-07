export type Role =
  | "candidate"
  | "employer"
  | "ministry_admin"
  | "training_provider"
  | "operator";

export type AuthUser = {
  id: string;
  email: string;
  role: Role;
};

export type CandidateProfile = {
  user_id: string;
  skills: string[];
  full_name: string | null;
  phone: string | null;
  location: string | null;
  education: string | null;
  experience: string | null;
  education_entries: EducationEntry[];
  experience_entries: ExperienceEntry[];
  professional_headline: string | null;
  employer_discoverable: boolean;
  updated_at: string | null;
};

export type EducationEntry = { degree: string; institution: string; field_of_study: string; start_date: string; end_date: string; currently_studying: boolean };
export type ExperienceEntry = { job_title: string; company: string; employment_type: string; location: string; start_date: string; end_date: string; currently_working: boolean; responsibilities: string };

export type CandidateProfileDraft = Omit<CandidateProfile, "user_id" | "updated_at" | "professional_headline" | "employer_discoverable">
  & Partial<Pick<CandidateProfile, "professional_headline" | "employer_discoverable">>;
export type CandidateAssistantMessage = {
  role: "user" | "assistant";
  content: string;
};
export type CandidateAssistantReply = {
  reply: string;
  profile_updates: Partial<CandidateProfileDraft>;
};
export type CandidateAssistantSession = {
  id: string;
  title: string;
  messages: CandidateAssistantMessage[];
  created_at: string;
  updated_at: string;
};
export type CandidateAssistantSessionSummary = Omit<CandidateAssistantSession, "messages">;

export type JobOffer = {
  id: string;
  title: string;
  description: string;
  location: string;
  required_skills: string[];
  preferred_skills?: string[];
  status?: "draft" | "published" | "paused" | "closed" | "expired" | "archived";
  employment_type?: string | null;
  workplace_arrangement?: string | null;
  positions_count?: number;
  salary_min?: number | null;
  salary_max?: number | null;
  application_deadline?: string | null;
  published_at?: string | null;
  created_at: string;
};

export type ServiceListingStatus = "draft" | "published" | "paused" | "archived";
export type ServiceListing = {
  id: string;
  owner_user_id: string;
  title: string;
  description: string;
  category: string;
  skills: string[];
  portfolio_items: PortfolioItem[];
  location: string | null;
  service_mode: "remote" | "provider_location" | "customer_location" | "flexible";
  price_type: "fixed" | "hourly" | "starting_at" | "quote" | "negotiable";
  price_min: string | null;
  price_max: string | null;
  status: ServiceListingStatus;
  created_at: string;
  updated_at: string;
};

export type ProfessionalProfile = {
  user_id: string;
  display_name: string;
  headline: string;
  introduction: string;
  photo_url: string | null;
  location: string | null;
  languages: string[];
  skills: string[];
  years_experience: number | null;
  visibility: "private" | "public";
  available: boolean;
  accepting_requests: boolean;
  availability: Record<string, unknown>;
  service_area: string[];
  portfolio_items: PortfolioItem[];
  created_at: string;
  updated_at: string;
};

export type PortfolioItem = { title: string; url: string; description: string };

export type PublicProfessional = Omit<ProfessionalProfile, "user_id" | "visibility" | "created_at" | "updated_at"> & {
  id: string;
  services: PublicService[];
};

export type PublicService = Omit<ServiceListing, "status" | "updated_at">;
export type ServiceRequestStatus = "requested" | "accepted" | "declined" | "in_progress" | "completion_requested" | "completed" | "cancelled" | "disputed";
export type ServiceRequest = { id: string; service_id: string; service_title: string; requester_user_id: string; provider_user_id: string; description: string; location: string | null; preferred_date: string | null; budget: string | null; attachments: string[]; agreed_scope: string | null; report_reason: string | null; status: ServiceRequestStatus; created_at: string; updated_at: string };
export type ServiceReview = { id: string; provider_user_id: string; rating: number; comment: string | null; created_at: string };
export type PublicCourse = Pick<TrainingCourse, "id" | "title" | "summary" | "skills" | "delivery_mode" | "location" | "starts_on" | "ends_on" | "duration_hours" | "price_tnd">;

export type MissionStatus = "draft" | "published" | "in_progress" | "completed" | "cancelled" | "expired" | "archived";
export type MissionProposalStatus = "submitted" | "under_review" | "accepted" | "rejected" | "withdrawn";
export type Mission = {
  id: string; publisher_user_id: string; organisation_id: string | null; title: string; description: string;
  category: string; required_skills: string[]; location: string | null; work_mode: "remote" | "on_site" | "hybrid" | "flexible";
  budget_type: "fixed" | "hourly" | "starting_at" | "quote" | "negotiable"; budget_min: string | null; budget_max: string | null;
  expected_start_date: string | null; deadline: string | null; duration: string | null; workers_needed: number;
  status: MissionStatus; created_at: string; updated_at: string;
};
export type PublicMission = Omit<Mission, "publisher_user_id" | "organisation_id" | "status" | "updated_at">;
export type MissionProposal = { id: string; mission_id: string; provider_user_id: string; message: string; proposed_price: string | null; estimated_duration: string | null; portfolio_references: string[]; availability: string | null; status: MissionProposalStatus; created_at: string; updated_at: string };

export type PublicJobSearchPage = {
  items: JobOffer[];
  total: number;
  limit: number;
  offset: number;
};

export type OrganisationProfile = {
  id: string;
  organisation_type: string;
  verification_status?: string;
  name: string;
  website: string | null;
  sector: string | null;
  size: string | null;
  description: string | null;
  phone: string | null;
  contact_email: string | null;
  location: string | null;
  profile_details: Record<string, unknown>;
};

export type JobMatch = JobOffer & {
  match_score: number;
  matched_skills: string[];
  missing_skills: string[];
};

export type JobApplicationStatus =
  | "submitted"
  | "reviewing"
  | "shortlisted"
  | "interview"
  | "interview_completed"
  | "offer_made"
  | "hired"
  | "rejected"
  | "withdrawn";

export type JobApplication = {
  id: string;
  job_offer_id: string;
  job_title: string;
  location: string;
  status: JobApplicationStatus;
  created_at: string;
  updated_at: string;
};

export type EmployerApplication = JobApplication & {
  candidate_name: string | null;
  candidate_location: string | null;
  candidate_skills: string[];
};

export type CandidateDiscovery = {
  candidate_id: string;
  professional_headline: string | null;
  skills: string[];
  location: string | null;
  experience_summary: Record<string, unknown>[];
  education_summary: Record<string, unknown>[];
  matched_skills: string[];
  missing_skills: string[];
};

export type TalentPool = { id: string; name: string; created_at: string; candidate_count: number };
export type TalentPoolMember = { candidate_id: string; professional_headline: string | null; skills: string[]; location: string | null; private_note: string | null; created_at: string };
export type ApplicationStatusHistory = { id: string; from_status: JobApplicationStatus | null; to_status: JobApplicationStatus; created_at: string };
export type EmployerApplicationDetail = EmployerApplication & {
  professional_headline: string | null;
  education_entries: Record<string, unknown>[];
  experience_entries: Record<string, unknown>[];
  status_history: ApplicationStatusHistory[];
};
export type ApplicationNote = { id: string; content: string; created_at: string };
export type ApplicationEvaluation = { id: string; criteria: Record<string, unknown>[]; strengths: string | null; concerns: string | null; updated_at: string };
export type JobOfferDecision = { id: string; application_id: string; job_title: string; status: "pending" | "accepted" | "declined" | "expired" | "withdrawn"; offered_at: string; response_deadline: string | null; proposed_conditions: Record<string, unknown>; responded_at: string | null };
export type Conversation = { id: string; application_id: string; candidate_name: string | null; job_title: string; updated_at: string; unread_count: number };
export type ConversationMessage = { id: string; sender_id: string; content: string; created_at: string; read_at: string | null };
export type EmployerInterview = { id: string; application_id: string; job_title: string; candidate_name: string | null; starts_at: string; duration_minutes: number; format: "online" | "in_person"; meeting_details: string | null; status: string };
export type EmployerNotification = { id: string; notification_type: string; title: string; body: string; resource_type: string | null; resource_id: string | null; read_at: string | null; created_at: string };
export type NotificationPreference = { notification_type: string; enabled: boolean };
export type OrganisationVerification = { id: string; organisation_id?: string | null; organisation_name?: string | null; status: string; supporting_information: string; evidence_url: string | null; reviewer_note: string | null; created_at: string };
export type EmployerAnalytics = {
  total_applications: number;
  applications_by_status: Record<string, number>;
  applications_per_offer: { job_offer_id: string; title: string; applications: number }[];
  shortlisted: number;
  interviews: number;
  hires_reported: number;
  rejected: number;
  withdrawn: number;
  application_to_interview_percent: number | null;
  interview_to_hire_percent: number | null;
  average_time_to_first_review_hours: number | null;
  has_sufficient_data: boolean;
};

export type CourseStatus = "draft" | "published" | "archived";
export type CourseDeliveryMode = "online" | "in_person" | "hybrid";
export type CourseEnrollmentStatus = "enrolled" | "completed" | "withdrawn";

export type TrainingCourse = {
  id: string;
  title: string;
  summary: string;
  skills: string[];
  delivery_mode: CourseDeliveryMode;
  location: string | null;
  starts_on: string | null;
  ends_on: string | null;
  duration_hours: number;
  capacity: number;
  price_tnd: string | null;
  status: CourseStatus;
  created_at: string;
  updated_at: string;
  enrollment_count: number;
  completed_count: number;
};

export type TrainingCourseDraft = Omit<
  TrainingCourse,
  "id" | "provider_id" | "created_at" | "updated_at" | "enrollment_count" | "completed_count"
>;

export type CourseEnrollment = {
  id: string;
  course_id: string;
  course_title: string;
  status: CourseEnrollmentStatus;
  created_at: string;
  updated_at: string;
};

export type ProviderCourseEnrollment = CourseEnrollment & {
  candidate_name: string | null;
  candidate_location: string | null;
  candidate_skills: string[];
};

export type AdminIndicators = {
  start_date: string | null;
  end_date: string | null;
  candidate_registrations: number;
  organisations: number;
  published_job_offers: number;
  applications_total: number;
  applications_by_status: { status: JobApplicationStatus; count: number }[];
  closed_applications: number;
  hired_applications: number;
  hire_rate_percent: number | null;
  top_skills: { skill: string; offer_count: number }[];
  published_courses: number;
  active_enrollments: number;
  course_completions: number;
};

export type CandidateRoadmapStep = {
  skill: string;
  skill_key: string;
  required_by: string[];
  offer_count: number;
  completed: boolean;
};

export type CandidateRoadmap = {
  steps: CandidateRoadmapStep[];
  completed_steps: number;
  total_steps: number;
  progress_percent: number;
};

export type CandidateInterviewRole = Pick<
  JobOffer,
  "id" | "title" | "description" | "location" | "required_skills"
>;

export type InterviewCompetency = {
  id: string;
  name: string;
  description: string;
  category: "hard" | "soft" | "communication";
  associated_skill: string | null;
  assessment_criteria: string[];
  required_proficiency_level: number | null;
  importance_weight: number | null;
  mandatory: boolean;
  source: "job_offer" | "platform_guidance";
  candidate_evidence: "self_reported" | "gap" | "not_assessed";
};

export type CandidateInterviewPreparationProfile = {
  role: CandidateInterviewRole;
  required_competencies: InterviewCompetency[];
  suggested_competencies: InterviewCompetency[];
  proficiency_levels: { level: number; name: string; description: string }[];
  cv_evidence: CandidateProfile | null;
  recommended_courses: {
    course: TrainingCourse;
    matching_skills: string[];
    reason: string;
  }[];
};

export type TechnicalAssessmentQuestion = {
  id: string;
  type: "knowledge" | "practical" | "scenario";
  format: "multiple_choice" | "short_answer" | "text_exercise";
  skill: string;
  prompt: string;
  options: { id: string; label: string }[];
  criteria: { id: string; label: string }[];
};

export type TechnicalAssessmentEvaluation = {
  score: number;
  max_score: number;
  criteria_scores: {
    criterion_id: string;
    label: string;
    score: number;
    max_score: number;
  }[];
  explanation: string;
  strengths: string[];
  weaknesses: string[];
  suggested_improvements: string[];
  method: "deterministic" | "llm";
};

export type CandidateTechnicalAssessment = {
  id: string;
  offer_id: string;
  offer_title: string;
  skill: string;
  status: "in_progress" | "completed";
  questions: TechnicalAssessmentQuestion[];
  answers: {
    question_id: string;
    answer: string;
    evaluation: TechnicalAssessmentEvaluation;
    created_at: string;
  }[];
  created_at: string;
  updated_at: string;
};

export type CandidateBehavioralAssessment = {
  id: string;
  offer_id: string;
  offer_title: string;
  competency_id: string;
  competency_name: string;
  status: "in_progress" | "completed";
  questions: {
    id: string;
    type: "behavioral" | "situational";
    format: "star_text" | "text_answer";
    competency_id: string;
    competency_name: string;
    prompt: string;
    criteria: { id: string; label: string }[];
    star_components: { id: string; label: string }[];
  }[];
  answers: {
    question_id: string;
    answer: string;
    evaluation: TechnicalAssessmentEvaluation & {
      star_scores: Record<string, { score: number; max_score: number; evidence: string }>;
    };
    created_at: string;
  }[];
  created_at: string;
  updated_at: string;
};

export type CandidateInterviewTranscription = {
  id: string;
  assessment_type: "technical" | "behavioral";
  assessment_id: string;
  question_id: string;
  status: "queued" | "processing" | "completed" | "failed";
  transcript: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
};

type LoginResponse = {
  access_token: string;
  user: AuthUser;
};

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

export const demoAccounts: { role: Role; label: string; email: string }[] = [
  { role: "candidate", label: "Candidat", email: "candidate@demo.maharamatch.test" },
  { role: "employer", label: "Employeur", email: "employer@demo.maharamatch.test" },
  { role: "ministry_admin", label: "Administration", email: "ministry@demo.maharamatch.test" },
  {
    role: "training_provider",
    label: "Organisme de formation",
    email: "provider@demo.maharamatch.test",
  },
  { role: "operator", label: "Opérations", email: "operator@demo.maharamatch.test" },
];

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function errorFromResponse(response: Response): Promise<ApiError> {
  const messageByStatus: Record<number, string> = {
    401: "Adresse e-mail ou mot de passe incorrect, ou session expirée.",
    403: "Votre rôle ne permet pas d’accéder à cette ressource.",
    409: "Un compte existe déjà avec cette adresse e-mail.",
    422: "Vérifiez les informations saisies.",
    502: "Le service d’assistance a renvoyé une réponse invalide.",
    503: "Le service est momentanément indisponible.",
  };
  const payload: unknown = await response.json().catch(() => undefined);
  const detail =
    typeof payload === "object" &&
    payload !== null &&
    "detail" in payload &&
    typeof payload.detail === "string"
      ? payload.detail
      : undefined;
  const message =
    response.status >= 500 && detail
      ? detail
      : messageByStatus[response.status] ??
        detail ??
        "Une erreur est survenue. Veuillez réessayer.";
  return new ApiError(message, response.status);
}

export async function login(email: string, password: string): Promise<LoginResponse> {
  const response = await fetch(`${API_BASE_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!response.ok) {
    throw await errorFromResponse(response);
  }
  return (await response.json()) as LoginResponse;
}

export async function registerCandidate(
  email: string,
  password: string,
): Promise<LoginResponse> {
  const response = await fetch(`${API_BASE_URL}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!response.ok) {
    throw await errorFromResponse(response);
  }
  return (await response.json()) as LoginResponse;
}

export async function fetchCurrentUser(token: string): Promise<AuthUser> {
  const response = await fetch(`${API_BASE_URL}/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) {
    throw await errorFromResponse(response);
  }
  return (await response.json()) as AuthUser;
}

export async function fetchPublicJobs(filters: {
  q?: string;
  location?: string;
  limit?: number;
  offset?: number;
} = {}): Promise<PublicJobSearchPage> {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if (value !== undefined && value !== "") params.set(key, String(value));
  }
  const response = await fetch(`${API_BASE_URL}/public/jobs?${params.toString()}`);
  if (!response.ok) throw await errorFromResponse(response);
  return (await response.json()) as PublicJobSearchPage;
}

export async function fetchPublicJob(offerId: string): Promise<JobOffer> {
  const response = await fetch(`${API_BASE_URL}/public/jobs/${encodeURIComponent(offerId)}`);
  if (!response.ok) throw await errorFromResponse(response);
  return (await response.json()) as JobOffer;
}

export async function fetchPublicCourse(courseId: string): Promise<PublicCourse> {
  const response = await fetch(`${API_BASE_URL}/public/training/${encodeURIComponent(courseId)}`);
  if (!response.ok) throw await errorFromResponse(response);
  return (await response.json()) as PublicCourse;
}

export async function fetchPublicService(serviceId: string): Promise<PublicService> {
  const response = await fetch(`${API_BASE_URL}/public/services/${encodeURIComponent(serviceId)}`);
  if (!response.ok) throw await errorFromResponse(response);
  return (await response.json()) as PublicService;
}

export async function createServiceRequest(token: string, serviceId: string, request: { description: string; location: string | null; preferred_date: string | null; budget: string | null; attachments: string[] }): Promise<ServiceRequest> {
  return authenticatedRequest(token, `/services/${encodeURIComponent(serviceId)}/requests`, { method: "POST", body: JSON.stringify(request) });
}
export function fetchMyServiceRequests(token: string): Promise<ServiceRequest[]> { return authenticatedRequest(token, "/service-requests/me"); }
export function updateServiceRequestStatus(token: string, id: string, status: ServiceRequestStatus, extra: { agreed_scope?: string | null; report_reason?: string | null } = {}): Promise<ServiceRequest> {
  return authenticatedRequest(token, `/service-requests/${encodeURIComponent(id)}/status`, { method: "PATCH", body: JSON.stringify({ status, ...extra }) });
}
export function createServiceReview(token: string, id: string, review: { rating: number; comment: string | null }): Promise<ServiceReview> {
  return authenticatedRequest(token, `/service-requests/${encodeURIComponent(id)}/review`, { method: "POST", body: JSON.stringify(review) });
}
export async function fetchProfessionalReviews(providerId: string): Promise<{ items: ServiceReview[]; average_rating: number | null; total: number }> {
  const response = await fetch(`${API_BASE_URL}/professionals/${encodeURIComponent(providerId)}/reviews`);
  if (!response.ok) throw await errorFromResponse(response);
  return (await response.json()) as { items: ServiceReview[]; average_rating: number | null; total: number };
}

export async function fetchPublicMissions(filters: { q?: string; location?: string; category?: string; skill?: string; work_mode?: string; limit?: number; offset?: number } = {}): Promise<{ items: PublicMission[]; total: number; limit: number; offset: number }> {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) if (value !== undefined && value !== "") params.set(key, String(value));
  const response = await fetch(`${API_BASE_URL}/public/missions?${params.toString()}`);
  if (!response.ok) throw await errorFromResponse(response);
  return (await response.json()) as { items: PublicMission[]; total: number; limit: number; offset: number };
}

export async function fetchPublicMission(missionId: string): Promise<PublicMission> {
  const response = await fetch(`${API_BASE_URL}/public/missions/${encodeURIComponent(missionId)}`);
  if (!response.ok) throw await errorFromResponse(response);
  return (await response.json()) as PublicMission;
}

export async function fetchPublicProfessional(profileId: string): Promise<PublicProfessional> {
  const response = await fetch(`${API_BASE_URL}/public/professionals/${encodeURIComponent(profileId)}`);
  if (!response.ok) throw await errorFromResponse(response);
  return (await response.json()) as PublicProfessional;
}

async function authenticatedRequest<T>(
  token: string,
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Authorization", `Bearer ${token}`);
  if (init.body && !(init.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers,
  });
  if (!response.ok) {
    throw await errorFromResponse(response);
  }
  return (await response.json()) as T;
}

export async function fetchPublicTraining(filters: { q?: string; location?: string; limit?: number; offset?: number } = {}): Promise<{ items: PublicCourse[]; total: number; limit: number; offset: number }> {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) if (value !== undefined && value !== "") params.set(key, String(value));
  const response = await fetch(`${API_BASE_URL}/public/training?${params.toString()}`);
  if (!response.ok) throw await errorFromResponse(response);
  return (await response.json()) as { items: PublicCourse[]; total: number; limit: number; offset: number };
}

export async function fetchPublicServices(filters: { q?: string; location?: string; category?: string; limit?: number; offset?: number } = {}): Promise<{ items: PublicService[]; total: number; limit: number; offset: number }> {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) if (value !== undefined && value !== "") params.set(key, String(value));
  const response = await fetch(`${API_BASE_URL}/public/services?${params.toString()}`);
  if (!response.ok) throw await errorFromResponse(response);
  return (await response.json()) as { items: PublicService[]; total: number; limit: number; offset: number };
}

export async function fetchPublicProfessionals(filters: { q?: string; location?: string; skill?: string; available?: boolean; limit?: number; offset?: number } = {}): Promise<{ items: PublicProfessional[]; total: number; limit: number; offset: number }> {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) if (value !== undefined && value !== "") params.set(key, String(value));
  const response = await fetch(`${API_BASE_URL}/public/professionals?${params.toString()}`);
  if (!response.ok) throw await errorFromResponse(response);
  return (await response.json()) as { items: PublicProfessional[]; total: number; limit: number; offset: number };
}

export function fetchMyProfessionalProfile(token: string): Promise<ProfessionalProfile> {
  return authenticatedRequest(token, "/me/professional-profile");
}

export function saveMyProfessionalProfile(token: string, profile: Omit<ProfessionalProfile, "user_id" | "created_at" | "updated_at">): Promise<ProfessionalProfile> {
  return authenticatedRequest(token, "/me/professional-profile", { method: "PUT", body: JSON.stringify(profile) });
}

export function fetchMyServices(token: string): Promise<ServiceListing[]> {
  return authenticatedRequest(token, "/me/services");
}

export function createMyService(token: string, service: Pick<ServiceListing, "title" | "description" | "category" | "skills" | "location" | "service_mode" | "price_type" | "price_min" | "price_max">): Promise<ServiceListing> {
  return authenticatedRequest(token, "/me/services", { method: "POST", body: JSON.stringify(service) });
}

export function updateMyService(token: string, serviceId: string, service: Pick<ServiceListing, "title" | "description" | "category" | "skills" | "location" | "service_mode" | "price_type" | "price_min" | "price_max">): Promise<ServiceListing> {
  return authenticatedRequest(token, `/me/services/${encodeURIComponent(serviceId)}`, { method: "PUT", body: JSON.stringify(service) });
}

export function updateMyServiceStatus(token: string, serviceId: string, status: ServiceListingStatus): Promise<ServiceListing> {
  return authenticatedRequest(token, `/me/services/${encodeURIComponent(serviceId)}/status`, { method: "PATCH", body: JSON.stringify({ status }) });
}

export function createMission(token: string, mission: Omit<Mission, "id" | "publisher_user_id" | "status" | "created_at" | "updated_at">): Promise<Mission> {
  return authenticatedRequest(token, "/missions", { method: "POST", body: JSON.stringify(mission) });
}
export function fetchMyMissions(token: string): Promise<Mission[]> { return authenticatedRequest(token, "/missions/me"); }
export function updateMissionStatus(token: string, id: string, status: MissionStatus): Promise<Mission> {
  return authenticatedRequest(token, `/missions/${encodeURIComponent(id)}/status`, { method: "PATCH", body: JSON.stringify({ status }) });
}
export function fetchMissionProposals(token: string, id: string): Promise<MissionProposal[]> {
  return authenticatedRequest(token, `/missions/${encodeURIComponent(id)}/proposals`);
}
export function fetchMyMissionProposals(token: string): Promise<MissionProposal[]> { return authenticatedRequest(token, "/mission-proposals/me"); }
export function submitMissionProposal(token: string, id: string, proposal: Pick<MissionProposal, "message" | "proposed_price" | "estimated_duration" | "portfolio_references" | "availability">): Promise<MissionProposal> {
  return authenticatedRequest(token, `/missions/${encodeURIComponent(id)}/proposals`, { method: "POST", body: JSON.stringify(proposal) });
}
export function updateMissionProposalStatus(token: string, missionId: string, proposalId: string, status: MissionProposalStatus): Promise<MissionProposal> {
  return authenticatedRequest(token, `/missions/${encodeURIComponent(missionId)}/proposals/${encodeURIComponent(proposalId)}`, { method: "PATCH", body: JSON.stringify({ status }) });
}

export function fetchCandidateProfile(token: string): Promise<CandidateProfile> {
  return authenticatedRequest(token, "/candidate/profile");
}

export function updateCandidateSkills(
  token: string,
  skills: string[],
): Promise<CandidateProfile> {
  return updateCandidateProfile(token, { skills });
}

export function updateCandidateProfile(
  token: string,
  profile: Partial<CandidateProfileDraft>,
): Promise<CandidateProfile> {
  return authenticatedRequest(token, "/candidate/profile", {
    method: "PUT",
    body: JSON.stringify(profile),
  });
}

export function uploadCandidateCv(token: string, file: File): Promise<CandidateProfile> {
  const form = new FormData();
  form.append("file", file, file.name);
  return authenticatedRequest(token, "/candidate/profile/cv", {
    method: "POST",
    body: form,
  });
}

export function sendCandidateAssistantMessage(
  token: string,
  messages: CandidateAssistantMessage[],
): Promise<CandidateAssistantReply> {
  return authenticatedRequest(token, "/candidate/assistant/chat", {
    method: "POST",
    body: JSON.stringify({ messages }),
  });
}

export function fetchCandidateAssistantSessions(
  token: string,
): Promise<CandidateAssistantSessionSummary[]> {
  return authenticatedRequest(token, "/candidate/assistant/sessions");
}

export function fetchCandidateAssistantSession(
  token: string,
  sessionId: string,
): Promise<CandidateAssistantSession> {
  return authenticatedRequest(token, `/candidate/assistant/sessions/${sessionId}`);
}

export function createCandidateAssistantSession(
  token: string,
): Promise<CandidateAssistantSession> {
  return authenticatedRequest(token, "/candidate/assistant/sessions", {
    method: "POST",
  });
}

export function sendCandidateAssistantSessionMessage(
  token: string,
  sessionId: string,
  content: string,
): Promise<CandidateAssistantSession> {
  return authenticatedRequest(token, `/candidate/assistant/sessions/${sessionId}/messages`, {
    method: "POST",
    body: JSON.stringify({ content }),
  });
}

export function renameCandidateAssistantSession(token: string, sessionId: string, title: string): Promise<CandidateAssistantSession> {
  return authenticatedRequest(token, `/candidate/assistant/sessions/${sessionId}`, {
    method: "PATCH",
    body: JSON.stringify({ title }),
  });
}

export async function deleteCandidateAssistantSession(
  token: string,
  sessionId: string,
): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/candidate/assistant/sessions/${sessionId}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) {
    throw await errorFromResponse(response);
  }
}

export function transcribeCandidateAudio(token: string, audio: Blob): Promise<{ text: string }> {
  const form = new FormData();
  form.append("audio", audio, "recording.webm");
  return authenticatedRequest(token, "/candidate/assistant/transcriptions", {
    method: "POST",
    body: form,
  });
}

export async function synthesizeCandidateSpeech(token: string, text: string): Promise<Blob> {
  const response = await fetch(`${API_BASE_URL}/candidate/assistant/speech`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ text }),
  });
  if (!response.ok) {
    throw await errorFromResponse(response);
  }
  return response.blob();
}

export function fetchCandidateMatches(token: string): Promise<JobMatch[]> {
  return authenticatedRequest(token, "/candidate/matches");
}

export function fetchCandidateRoadmap(token: string): Promise<CandidateRoadmap> {
  return authenticatedRequest(token, "/candidate/roadmap");
}

export function updateCandidateRoadmapStep(
  token: string,
  skill: string,
  completed: boolean,
): Promise<CandidateRoadmap> {
  return authenticatedRequest(token, "/candidate/roadmap/steps", {
    method: "PUT",
    body: JSON.stringify({ skill, completed }),
  });
}

export function fetchCandidateInterviewRoles(
  token: string,
): Promise<CandidateInterviewRole[]> {
  return authenticatedRequest(token, "/candidate/interview-prep/roles");
}

export function fetchCandidateInterviewPreparationProfile(
  token: string,
  offerId: string,
): Promise<CandidateInterviewPreparationProfile> {
  return authenticatedRequest(
    token,
    `/candidate/interview-prep/profiles/${encodeURIComponent(offerId)}`,
  );
}

export function startCandidateTechnicalAssessment(
  token: string,
  offerId: string,
  skill: string,
): Promise<CandidateTechnicalAssessment> {
  return authenticatedRequest(token, "/candidate/interview-prep/assessments", {
    method: "POST",
    body: JSON.stringify({ offer_id: offerId, skill }),
  });
}

export function submitCandidateTechnicalAssessmentAnswer(
  token: string,
  assessmentId: string,
  answer: { question_id: string; answer?: string; selected_option_id?: string },
): Promise<CandidateTechnicalAssessment> {
  return authenticatedRequest(
    token,
    `/candidate/interview-prep/assessments/${encodeURIComponent(assessmentId)}/answers`,
    {
      method: "POST",
      body: JSON.stringify(answer),
    },
  );
}

export function startCandidateBehavioralAssessment(
  token: string,
  offerId: string,
  competencyId: string,
): Promise<CandidateBehavioralAssessment> {
  return authenticatedRequest(token, "/candidate/interview-prep/behavioral-assessments", {
    method: "POST",
    body: JSON.stringify({ offer_id: offerId, skill: competencyId }),
  });
}

export function submitCandidateBehavioralAssessmentAnswer(
  token: string,
  assessmentId: string,
  questionId: string,
  answer: string,
): Promise<CandidateBehavioralAssessment> {
  return authenticatedRequest(
    token,
    `/candidate/interview-prep/behavioral-assessments/${encodeURIComponent(assessmentId)}/answers`,
    {
      method: "POST",
      body: JSON.stringify({ question_id: questionId, answer }),
    },
  );
}

export function uploadCandidateInterviewAudio(
  token: string,
  assessmentType: "technical" | "behavioral",
  assessmentId: string,
  questionId: string,
  audio: Blob,
): Promise<CandidateInterviewTranscription> {
  const form = new FormData();
  form.append("audio", audio, "interview-answer.webm");
  return authenticatedRequest(
    token,
    `/candidate/interview-prep/${assessmentType}-assessments/${encodeURIComponent(assessmentId)}` +
      `/questions/${encodeURIComponent(questionId)}/transcription`,
    {
      method: "POST",
      body: form,
    },
  );
}

export function fetchCandidateInterviewTranscription(
  token: string,
  transcriptionId: string,
): Promise<CandidateInterviewTranscription> {
  return authenticatedRequest(
    token,
    `/candidate/interview-prep/transcriptions/${encodeURIComponent(transcriptionId)}`,
  );
}

export function fetchEmployerOffers(token: string): Promise<JobOffer[]> {
  return authenticatedRequest(token, "/employer/offers");
}

export function fetchEmployerOrganisation(token: string): Promise<OrganisationProfile> {
  return authenticatedRequest(token, "/employer/organisation");
}

export function updateEmployerOrganisation(
  token: string,
  profile: Omit<OrganisationProfile, "id" | "organisation_type">,
): Promise<OrganisationProfile> {
  return authenticatedRequest(token, "/employer/organisation", {
    method: "PUT",
    body: JSON.stringify(profile),
  });
}

export function createEmployerOrganisation(
  token: string,
  profile: Omit<OrganisationProfile, "id" | "organisation_type">,
): Promise<OrganisationProfile> {
  return authenticatedRequest(token, "/employer/organisation", {
    method: "POST", body: JSON.stringify(profile),
  });
}

export function generateEmployerOffer(token: string, prompt: string): Promise<{
  title: string; description: string; location: string;
  required_skills: string[]; preferred_skills: string[];
}> {
  return authenticatedRequest(token, "/employer/offers/generate", {
    method: "POST", body: JSON.stringify({ prompt }),
  });
}

export function createEmployerOffer(
  token: string,
  offer: Pick<JobOffer, "title" | "description" | "location" | "required_skills">
    & Partial<Pick<JobOffer, "preferred_skills" | "status">>,
): Promise<JobOffer> {
  return authenticatedRequest(token, "/employer/offers", {
    method: "POST",
    body: JSON.stringify(offer),
  });
}

export function updateEmployerOfferStatus(
  token: string,
  offerId: string,
  nextStatus: NonNullable<JobOffer["status"]>,
): Promise<JobOffer> {
  return authenticatedRequest(token, `/employer/offers/${offerId}/status`, {
    method: "PATCH",
    body: JSON.stringify({ status: nextStatus }),
  });
}

export function applyToJob(token: string, offerId: string): Promise<JobApplication> {
  return authenticatedRequest(token, `/candidate/applications/${offerId}`, {
    method: "POST",
  });
}

export function fetchCandidateApplications(token: string): Promise<JobApplication[]> {
  return authenticatedRequest(token, "/candidate/applications");
}

export function fetchCandidateOfferDecisions(token: string): Promise<JobOfferDecision[]> {
  return authenticatedRequest(token, "/candidate/offer-decisions");
}

export function respondToJobOffer(token: string, decisionId: string, status: "accepted" | "declined"): Promise<JobOfferDecision> {
  return authenticatedRequest(token, `/candidate/offer-decisions/${decisionId}`, { method: "PATCH", body: JSON.stringify({ status }) });
}

export function withdrawCandidateApplication(token: string, applicationId: string): Promise<JobApplication> {
  return authenticatedRequest(token, `/candidate/applications/${applicationId}/withdraw`, {
    method: "POST",
  });
}

export function fetchEmployerApplications(token: string): Promise<EmployerApplication[]> {
  return authenticatedRequest(token, "/employer/applications");
}

export function searchEmployerCandidates(token: string, filters: { q?: string; skill?: string; location?: string; offer_id?: string }): Promise<CandidateDiscovery[]> {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) if (value) params.set(key, value);
  const suffix = params.size ? `?${params.toString()}` : "";
  return authenticatedRequest(token, `/employer/candidates${suffix}`);
}

export function fetchTalentPools(token: string): Promise<TalentPool[]> {
  return authenticatedRequest(token, "/employer/talent-pools");
}

export function createTalentPool(token: string, name: string): Promise<TalentPool> {
  return authenticatedRequest(token, "/employer/talent-pools", { method: "POST", body: JSON.stringify({ name }) });
}

export function addCandidateToTalentPool(token: string, poolId: string, candidateId: string, privateNote?: string): Promise<{ id: string; candidate_id: string }> {
  return authenticatedRequest(token, `/employer/talent-pools/${poolId}/members`, { method: "POST", body: JSON.stringify({ candidate_id: candidateId, private_note: privateNote ?? null }) });
}

export function fetchTalentPoolMembers(token: string, poolId: string): Promise<TalentPoolMember[]> {
  return authenticatedRequest(token, `/employer/talent-pools/${poolId}/members`);
}

export function removeTalentPoolMember(token: string, poolId: string, candidateId: string): Promise<void> {
  return authenticatedRequest(token, `/employer/talent-pools/${poolId}/members/${candidateId}`, { method: "DELETE" });
}

export function fetchEmployerApplicationDetail(token: string, applicationId: string): Promise<EmployerApplicationDetail> {
  return authenticatedRequest(token, `/employer/applications/${applicationId}/detail`);
}

export function fetchApplicationNotes(token: string, applicationId: string): Promise<ApplicationNote[]> {
  return authenticatedRequest(token, `/employer/applications/${applicationId}/notes`);
}

export function addApplicationNote(token: string, applicationId: string, content: string): Promise<ApplicationNote> {
  return authenticatedRequest(token, `/employer/applications/${applicationId}/notes`, { method: "POST", body: JSON.stringify({ content }) });
}

export function fetchApplicationEvaluation(token: string, applicationId: string): Promise<ApplicationEvaluation | null> {
  return authenticatedRequest(token, `/employer/applications/${applicationId}/evaluation`);
}

export function saveApplicationEvaluation(token: string, applicationId: string, value: Pick<ApplicationEvaluation, "criteria" | "strengths" | "concerns">): Promise<ApplicationEvaluation> {
  return authenticatedRequest(token, `/employer/applications/${applicationId}/evaluation`, { method: "PUT", body: JSON.stringify(value) });
}

export function createFormalOffer(token: string, applicationId: string, value: { response_deadline: string | null; proposed_conditions: Record<string, unknown> }): Promise<JobOfferDecision> {
  return authenticatedRequest(token, `/employer/applications/${applicationId}/offer-decision`, { method: "POST", body: JSON.stringify(value) });
}

export function ensureApplicationConversation(token: string, applicationId: string): Promise<Conversation> {
  return authenticatedRequest(token, `/applications/${applicationId}/conversation`, { method: "POST" });
}

export function fetchEmployerConversations(token: string): Promise<Conversation[]> {
  return authenticatedRequest(token, "/employer/conversations");
}

export function fetchConversationMessages(token: string, conversationId: string): Promise<ConversationMessage[]> {
  return authenticatedRequest(token, `/conversations/${conversationId}/messages`);
}

export function sendConversationMessage(token: string, conversationId: string, content: string): Promise<ConversationMessage> {
  return authenticatedRequest(token, `/conversations/${conversationId}/messages`, { method: "POST", body: JSON.stringify({ content }) });
}

export function fetchEmployerInterviews(token: string): Promise<EmployerInterview[]> {
  return authenticatedRequest(token, "/employer/interviews");
}

export function createEmployerInterview(token: string, value: { application_id: string; starts_at: string; duration_minutes: number; format: "online" | "in_person"; meeting_details: string | null }): Promise<EmployerInterview> {
  return authenticatedRequest(token, "/employer/interviews", { method: "POST", body: JSON.stringify(value) });
}

export function updateEmployerInterviewStatus(token: string, interviewId: string, status: string): Promise<EmployerInterview> {
  return authenticatedRequest(token, `/employer/interviews/${interviewId}/status`, { method: "PATCH", body: JSON.stringify({ status }) });
}

export function fetchEmployerNotifications(token: string): Promise<EmployerNotification[]> {
  return authenticatedRequest(token, "/employer/notifications");
}

export function markEmployerNotificationRead(token: string, notificationId: string): Promise<EmployerNotification> {
  return authenticatedRequest(token, `/employer/notifications/${notificationId}/read`, { method: "PATCH" });
}

export function fetchNotificationPreferences(token: string): Promise<NotificationPreference[]> {
  return authenticatedRequest(token, "/employer/notification-preferences");
}

export function updateNotificationPreference(token: string, name: string, enabled: boolean): Promise<NotificationPreference> {
  return authenticatedRequest(token, `/employer/notification-preferences/${name}`, { method: "PUT", body: JSON.stringify({ enabled }) });
}

export function submitOrganisationVerification(token: string, value: { supporting_information: string; evidence_url: string | null }): Promise<OrganisationVerification> {
  return authenticatedRequest(token, "/employer/organisation/verification", { method: "POST", body: JSON.stringify(value) });
}

export function fetchPendingOrganisationVerifications(token: string): Promise<OrganisationVerification[]> {
  return authenticatedRequest(token, "/admin/organisations/verification");
}

export function reviewOrganisationVerification(token: string, id: string, status: "verified" | "rejected", reviewer_note: string): Promise<OrganisationVerification> {
  return authenticatedRequest(token, `/admin/organisations/verification/${id}`, { method: "PATCH", body: JSON.stringify({ status, reviewer_note }) });
}

export function fetchEmployerAnalytics(token: string): Promise<EmployerAnalytics> {
  return authenticatedRequest(token, "/employer/analytics");
}

export function updateEmployerApplicationStatus(
  token: string,
  applicationId: string,
  status: Exclude<JobApplicationStatus, "submitted">,
): Promise<JobApplication> {
  return authenticatedRequest(token, `/employer/applications/${applicationId}/status`, {
    method: "PUT",
    body: JSON.stringify({ status }),
  });
}

export function fetchAdminIndicators(
  token: string,
  startDate: string,
  endDate: string,
): Promise<AdminIndicators> {
  const query = new URLSearchParams();
  if (startDate) query.set("start_date", startDate);
  if (endDate) query.set("end_date", endDate);
  const queryString = query.toString();
  const suffix = queryString ? `?${queryString}` : "";
  return authenticatedRequest(token, `/admin/indicators${suffix}`);
}

export function fetchTrainingCourses(token: string): Promise<TrainingCourse[]> {
  return authenticatedRequest(token, "/training/courses");
}

export function createTrainingCourse(
  token: string,
  course: TrainingCourseDraft,
): Promise<TrainingCourse> {
  return authenticatedRequest(token, "/training/courses", {
    method: "POST",
    body: JSON.stringify(course),
  });
}

export function updateTrainingCourse(
  token: string,
  courseId: string,
  course: TrainingCourseDraft,
): Promise<TrainingCourse> {
  return authenticatedRequest(token, `/training/courses/${courseId}`, {
    method: "PUT",
    body: JSON.stringify(course),
  });
}

export function fetchProviderCourseEnrollments(
  token: string,
  courseId: string,
): Promise<ProviderCourseEnrollment[]> {
  return authenticatedRequest(token, `/training/courses/${courseId}/enrollments`);
}

export function updateCourseEnrollmentStatus(
  token: string,
  enrollmentId: string,
  status: CourseEnrollmentStatus,
): Promise<ProviderCourseEnrollment> {
  return authenticatedRequest(token, `/training/enrollments/${enrollmentId}/status`, {
    method: "PUT",
    body: JSON.stringify({ status }),
  });
}

export function fetchPublishedCourses(token: string): Promise<TrainingCourse[]> {
  return authenticatedRequest(token, "/candidate/courses");
}

export function fetchCandidateEnrollments(token: string): Promise<CourseEnrollment[]> {
  return authenticatedRequest(token, "/candidate/enrollments");
}

export function enrollInCourse(token: string, courseId: string): Promise<CourseEnrollment> {
  return authenticatedRequest(token, `/candidate/courses/${courseId}/enroll`, {
    method: "POST",
  });
}
