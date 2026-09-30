import { supabase } from './supabase'

export const API_BASE_URL: string = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8006'

export class ApiError extends Error {
  status: number

  constructor(status: number) {
    super(`HTTP ${status}`)
    this.status = status
  }
}

/** Calls the backend with the Supabase access token. A 401 means the login is no longer valid: sign out. */
export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const { data } = await supabase.auth.getSession()
  const headers = new Headers(init.headers)
  if (data.session) headers.set('Authorization', `Bearer ${data.session.access_token}`)

  const response = await fetch(`${API_BASE_URL}/api/v1${path}`, { ...init, headers })
  if (response.status === 401) {
    await supabase.auth.signOut({ scope: 'local' })
  }
  if (!response.ok) throw new ApiError(response.status)
  return response.json()
}

export type Health = { status: string; governorates: number }

export async function getHealth(): Promise<Health> {
  const response = await fetch(`${API_BASE_URL}/api/v1/health`)
  if (!response.ok) throw new Error(`HTTP ${response.status}`)
  return response.json()
}

export type Me = { id: string; email: string; name: string | null; has_profile: boolean }

export function getMe(): Promise<Me> {
  return api<Me>('/me')
}

export type Governorate = { code: string; name_fr: string; name_ar: string }
export type ProfileSkill = {
  code: string
  label_fr: string
  skill_type: 'hard' | 'soft' | 'language'
  level: number
  source: 'self_declared' | 'cv'
  confidence: number | null
}
export type Experience = {
  id: string
  job_title_raw: string
  employer_name: string | null
  start_date: string | null
  end_date: string | null
  duration_months: number | null
  description: string | null
}
export type Education = {
  id: string
  level: string | null
  field_of_study: string | null
  institution: string | null
  graduation_year: number | null
}
export type Profile = {
  full_name: string | null
  email: string | null
  phone: string | null
  onboarding_path: 'cv_upload' | 'derja_detailed'
  literacy_level: string
  governorate: Governorate | null
  education_level: string | null
  years_experience: number | null
  languages: { code: string; level: string }[]
  summary: string | null
  available_from: string | null
  consent_version: string | null
  consent_given_at: string | null
  skills: ProfileSkill[]
  experiences: Experience[]
  educations: Education[]
  desired_occupations: { code: string; title_fr: string; priority: number | null }[]
}

/** The candidate's profile, or null when it hasn't been created yet (404). */
export async function getProfile(): Promise<Profile | null> {
  try {
    return await api<Profile>('/me/profile')
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) return null
    throw error
  }
}
