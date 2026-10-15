export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'
export const ONBOARDING_SESSION_KEY = 'mahara_onboarding_session_id'

export type SkillGap = {
  skill_code: string
  gap_type: 'missing' | 'insufficient_level'
  requirement: 'required' | 'preferred'
  required_level: number
  current_level: number | null
}

export type MatchResult = {
  match_id: string | null
  candidate_id: string
  job_offer_id: string
  score_global: number
  breakdown: {
    hard_skills: number
    experience: number
    soft_skills: number
    location: number
  }
  weights: {
    hard_skills: number
    experience: number
    soft_skills: number
    location: number
  }
  gaps: SkillGap[]
  model_version: string
  computed_at: string
}

export type RankedMatches = {
  subject_id: string
  subject_type: 'candidate'
  items: MatchResult[]
  generated_at: string
}

export type Roadmap = {
  roadmap_id: string | null
  candidate_id: string
  target_job_offer_id: string | null
  target_occupation_code: string | null
  status: string
  progress_pct: number
  steps: { position: number; skill_code: string; status: string }[]
  model_version: string
}

export type MatchRoadmap = Roadmap | { status: 'no_gap'; message: string }

export type MatchAssistantMessage = { role: 'user' | 'assistant'; content: string }
export type MatchAssistantSource = {
  id: string
  type: string
  title: string
  excerpt: string
  citation: string
  similarity: number
}
export type MatchAssistantResponse = { reply: string; sources: MatchAssistantSource[] }

export type CandidateApplication = {
  application_id: string
  job_offer_id: string
  title: string
  status: string
  applied_at: string
  employer_contact_consent?: boolean
}

export type EmployerApplication = CandidateApplication & {
  candidate_id: string
  candidate_name: string | null
  candidate_email: string | null
  candidate_phone: string | null
  match_id: string | null
  score_global: number | null
  employer_contact_consent: boolean
}

export type EmployerOffer = {
  job_offer_id: string
  title: string
  status: string
  published_at: string | null
  expires_at: string | null
  applications_count: number
  submitted_count: number
  shortlisted_count: number
  hired_count: number
  rejected_count: number
  top_match_score: number | null
  archived_at?: string | null
}

export type MockInterviewQuestion = { theme: string; prompt: string; follow_up: string; tip: string }
export type MockInterviewFeedback = {
  overall_summary: string
  topics: { title: string; status: string; evidence: string; next_step: string }[]
  answers: { question_index: number; strength: string; improvement: string; example: string }[]
}
export type MockInterview = {
  session_id: string; target_title: string; occupation_code: string | null; target_offer_id: string | null; language: 'fr' | 'ar' | 'derja'
  question_count: number; questions: MockInterviewQuestion[]; answers: { question_index: number; answer: string }[]
  current_index: number; draft_answer: string | null; status: 'in_progress' | 'completed'; saved: boolean; feedback: MockInterviewFeedback | null
}

export function getMockInterviews(): Promise<{ items: MockInterview[] }> {
  return requestJson('/api/v1/me/mock-interviews')
}

export function startMockInterview(input: { target_title: string; occupation_code: string | null; target_offer_id: string | null; language: 'fr' | 'ar' | 'derja'; question_count: number; consent: boolean }): Promise<MockInterview> {
  return requestJson('/api/v1/me/mock-interviews', { method: 'POST', body: JSON.stringify(input) })
}

export function getMockInterview(id: string): Promise<MockInterview> {
  return requestJson(`/api/v1/me/mock-interviews/${encodeURIComponent(id)}`)
}

export function submitMockInterviewAnswer(id: string, question_index: number, answer: string): Promise<MockInterview & { next_question: MockInterviewQuestion | null }> {
  return requestJson(`/api/v1/me/mock-interviews/${encodeURIComponent(id)}/answers`, { method: 'POST', body: JSON.stringify({ question_index, answer }) })
}

export function saveMockInterviewDraftAnswer(id: string, answer: string): Promise<MockInterview> {
  return requestJson(`/api/v1/me/mock-interviews/${encodeURIComponent(id)}/draft-answer`, { method: 'PATCH', body: JSON.stringify({ answer }) })
}

export function reviewMockInterview(id: string): Promise<MockInterview> {
  return requestJson(`/api/v1/me/mock-interviews/${encodeURIComponent(id)}/review`, { method: 'POST' })
}

export function saveMockInterview(id: string, saved: boolean): Promise<MockInterview> {
  return requestJson(`/api/v1/me/mock-interviews/${encodeURIComponent(id)}/saved`, { method: 'PATCH', body: JSON.stringify({ saved }) })
}

export function deleteMockInterview(id: string): Promise<void> {
  return requestJson(`/api/v1/me/mock-interviews/${encodeURIComponent(id)}`, { method: 'DELETE' })
}

export async function downloadMockInterviewReport(id: string): Promise<Blob> {
  const token = localStorage.getItem('mahara_access_token')
  const response = await fetch(`${API_BASE_URL}/api/v1/me/mock-interviews/${encodeURIComponent(id)}/report.pdf`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new Error(body?.detail || `Request failed with status ${response.status}`)
  }
  return response.blob()
}

export type EmployerOfferEditor = {
  offer_id: string; employer_id: string; title: string; description: string
  occupation_code: string | null; sector_code: string | null; contract_type: string; work_mode: string
  location: { governorate_code: string; delegation: string | null }; positions_count: number
  min_years_experience: number; education_level_min: string | null
  salary: { min_tnd: number | null; max_tnd: number | null; period: 'hour' | 'day' | 'month' } | null
  skills: { skill_code: string; requirement: string; min_level: number }[]
  languages_required: { code: string; level: number }[]; status: string; source: string
  published_at: string | null; expires_at: string | null
}

export type EmployerApplicationDetail = {
  application_id: string
  status: string
  applied_at: string
  cover_note: string | null
  job_offer: { job_offer_id: string; title: string }
  candidate: {
    candidate_id: string
    name: string | null
    email: string | null
    phone: string | null
    summary: string | null
    governorate: string | null
    education_level: string | null
    years_experience: number | null
    languages: { code: string; level: number }[]
    available_from: string | null
    desired_occupations: { code: string; title: string }[]
    skills: { code: string; label: string; level: number; source: string; confidence: number }[]
    experience: { title: string; description: string | null; duration_months: number | null; informal: boolean }[]
    education: { level: string; field_of_study: string | null; graduation_year: number | null }[]
  }
  match: null | {
    match_id: string
    score_global: number
    breakdown: { hard_skills: number; experience: number; soft_skills: number; location: number }
    computed_at: string
    gaps: { skill_code: string; label: string; gap_type: string; requirement: string; required_level: number; current_level: number | null }[]
  }
}

export async function requestJson<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  const token = localStorage.getItem('mahara_access_token')
  if (token && !headers.has('Authorization')) headers.set('Authorization', `Bearer ${token}`)
  if (!headers.has('Content-Type') && init.body && !(init.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json')
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers,
  })

  if (!response.ok) {
    const body = await response.json().catch(() => null)
    const detail = body?.detail
    const message = typeof detail === 'string' ? detail : detail?.message
    throw new Error(typeof message === 'string' ? message : `Request failed with status ${response.status}`)
  }

  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

export function getMyMatches(): Promise<RankedMatches> {
  return requestJson<RankedMatches>('/api/v1/me/matches')
}

export function getMyRoadmap(jobOfferId: string): Promise<MatchRoadmap> {
  return requestJson<MatchRoadmap>(`/api/v1/me/matches/${encodeURIComponent(jobOfferId)}/roadmap`)
}

export function askAboutMatch(
  jobOfferId: string,
  question: string,
  history: MatchAssistantMessage[],
): Promise<MatchAssistantResponse> {
  return requestJson<MatchAssistantResponse>(`/api/v1/me/matches/${encodeURIComponent(jobOfferId)}/assistant`, {
    method: 'POST',
    body: JSON.stringify({ question, history }),
  })
}

export function getMyApplications(): Promise<CandidateApplication[]> {
  return requestJson<CandidateApplication[]>('/api/v1/me/applications')
}

export function applyToOffer(jobOfferId: string, employerContactConsent: boolean): Promise<CandidateApplication> {
  return requestJson<CandidateApplication>('/api/v1/me/applications', {
    method: 'POST',
    body: JSON.stringify({ job_offer_id: jobOfferId, employer_contact_consent: employerContactConsent }),
  })
}

export function getEmployerApplications(): Promise<EmployerApplication[]> {
  return requestJson<EmployerApplication[]>('/api/v1/employer/applications')
}

export function getEmployerOffers(): Promise<EmployerOffer[]> {
  return requestJson<EmployerOffer[]>('/api/v1/employer/offers')
}

export function getEmployerApplication(applicationId: string): Promise<EmployerApplicationDetail> {
  return requestJson<EmployerApplicationDetail>(`/api/v1/employer/applications/${encodeURIComponent(applicationId)}`)
}

export function decideApplication(
  applicationId: string,
  decision: 'shortlisted' | 'hired' | 'rejected' | 'no_show',
): Promise<{ application_id: string; status: string }> {
  return requestJson<{ application_id: string; status: string }>(`/api/v1/employer/applications/${encodeURIComponent(applicationId)}`, {
    method: 'PATCH',
    body: JSON.stringify({ decision }),
  })
}

export function updateApplicationContactConsent(applicationId: string, allowContact: boolean): Promise<{ application_id: string; employer_contact_consent: boolean }> {
  return requestJson(`/api/v1/me/applications/${encodeURIComponent(applicationId)}/contact-consent`, {
    method: 'PATCH', body: JSON.stringify({ allow_contact: allowContact }),
  })
}

export function getEmployerOfferEditor(offerId: string): Promise<EmployerOfferEditor> {
  return requestJson<EmployerOfferEditor>(`/api/v1/employer/offers/${encodeURIComponent(offerId)}/edit`)
}

export function updateEmployerOffer(offerId: string, offer: EmployerOfferEditor): Promise<EmployerOfferEditor> {
  return requestJson<EmployerOfferEditor>(`/api/v1/employer/offers/${encodeURIComponent(offerId)}`, {
    method: 'PUT', body: JSON.stringify(offer),
  })
}

export function archiveEmployerOffer(offerId: string): Promise<{ status: string }> {
  return requestJson<{ status: string }>(`/api/v1/employer/offers/${encodeURIComponent(offerId)}/archive`, { method: 'POST' })
}

export function setEmployerOfferStatus(offerId: string, status: 'published' | 'closed', expiresAt?: string | null): Promise<{ job_offer_id: string; status: string }> {
  return requestJson(`/api/v1/employer/offers/${encodeURIComponent(offerId)}/status`, {
    method: 'PATCH', body: JSON.stringify({ status, ...(expiresAt !== undefined ? { expires_at: expiresAt } : {}) }),
  })
}

export function inviteCandidateToInterview(applicationId: string, invitation: { meeting_at_local: string; timezone: string; note?: string }): Promise<{ notification_id: string; status: string }> {
  return requestJson<{ notification_id: string; status: string }>(`/api/v1/employer/applications/${encodeURIComponent(applicationId)}/interviews`, {
    method: 'POST', body: JSON.stringify(invitation),
  })
}

export function getInterviewInvitations(applicationId: string): Promise<{ notification_id: string; status: string; meeting_at: string; meeting_timezone: string; attempts: number; sent_at: string | null }[]> {
  return requestJson(`/api/v1/employer/applications/${encodeURIComponent(applicationId)}/interviews`)
}
