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

export type CandidateApplication = {
  application_id: string
  job_offer_id: string
  title: string
  status: string
  applied_at: string
}

export type EmployerApplication = CandidateApplication & {
  candidate_id: string
  candidate_name: string | null
  candidate_email: string | null
  candidate_phone: string | null
  match_id: string | null
  score_global: number | null
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

export function getMyApplications(): Promise<CandidateApplication[]> {
  return requestJson<CandidateApplication[]>('/api/v1/me/applications')
}

export function applyToOffer(jobOfferId: string): Promise<CandidateApplication> {
  return requestJson<CandidateApplication>('/api/v1/me/applications', {
    method: 'POST',
    body: JSON.stringify({ job_offer_id: jobOfferId }),
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
