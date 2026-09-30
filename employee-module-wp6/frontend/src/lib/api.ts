import { supabase } from './supabase'

export const API_BASE_URL: string = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8006'

export class ApiError extends Error {
  status: number
  /** FastAPI's `detail`: a string, or for 422 a list of `{loc, msg, type}`. */
  detail: unknown

  constructor(status: number, detail: unknown = null) {
    super(`HTTP ${status}`)
    this.status = status
    this.detail = detail
  }
}

/** Calls the backend with the Supabase access token. A 401 means the login is no longer valid: sign out. */
async function request(path: string, init: RequestInit = {}): Promise<Response> {
  const { data } = await supabase.auth.getSession()
  const headers = new Headers(init.headers)
  if (data.session) headers.set('Authorization', `Bearer ${data.session.access_token}`)

  const response = await fetch(`${API_BASE_URL}/api/v1${path}`, { ...init, headers })
  if (response.status === 401) {
    await supabase.auth.signOut({ scope: 'local' })
  }
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new ApiError(response.status, body?.detail ?? null)
  }
  return response
}

/** Same as request(), for endpoints that answer JSON. */
export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  return (await request(path, init)).json()
}

export type Health = { status: string; governorates: number }

export async function getHealth(): Promise<Health> {
  const response = await fetch(`${API_BASE_URL}/api/v1/health`)
  if (!response.ok) throw new Error(`HTTP ${response.status}`)
  return response.json()
}

export type Me = { id: string; email: string; name: string | null; has_profile: boolean }

/**
 * Calls made while the same call is still running share its answer (React's StrictMode runs effects
 * twice in development, and each request is a slow trip to the database).
 */
function shared<T>(load: () => Promise<T>): () => Promise<T> {
  let running: Promise<T> | null = null
  return () => {
    running ??= load().finally(() => {
      running = null
    })
    return running
  }
}

export const getMe = shared(() => api<Me>('/me'))

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
  /** An uploaded photo exists (getPhoto); otherwise the Google photo is shown. */
  has_photo: boolean
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
export const getProfile = shared(async (): Promise<Profile | null> => {
  try {
    return await api<Profile>('/me/profile')
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) return null
    throw error
  }
})

export type ProfileIn = {
  consent: boolean
  from_cv: boolean
  full_name: string
  email: string | null
  phone: string | null
  governorate_code: string | null
  education_level: string | null
  years_experience: number | null
  languages: { code: string; level: string }[]
  summary: string | null
  available_from: string | null
  skills: { code: string; level: number; source: ProfileSkill['source']; confidence: number | null }[]
  experiences: Omit<Experience, 'id'>[]
  educations: Omit<Education, 'id'>[]
  desired_occupations: { code: string; priority: number }[]
}

/** Saves the whole profile (skills, experiences... are replaced) and returns it as stored. */
export function saveProfile(body: ProfileIn): Promise<Profile> {
  return api<Profile>('/me/profile', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

export type SkillOption = { code: string; label_fr: string; skill_type: ProfileSkill['skill_type'] }
export type OccupationOption = { code: string; title_fr: string }

// Reference data barely changes, and every request costs a trip to the database: keep answers in memory
// for the whole visit. A failed request is forgotten so the next call tries again.
const referenceCache = new Map<string, Promise<unknown>>()

function cachedApi<T>(path: string): Promise<T> {
  let answer = referenceCache.get(path) as Promise<T> | undefined
  if (!answer) {
    answer = api<T>(path)
    answer.catch(() => referenceCache.delete(path))
    referenceCache.set(path, answer)
  }
  return answer
}

export function getGovernorates(): Promise<Governorate[]> {
  return cachedApi<Governorate[]>('/reference/governorates')
}

export function searchSkills(q: string): Promise<SkillOption[]> {
  return cachedApi<SkillOption[]>(`/reference/skills?q=${encodeURIComponent(q.toLowerCase())}`)
}

export function searchOccupations(q: string): Promise<OccupationOption[]> {
  return cachedApi<OccupationOption[]>(`/reference/occupations?q=${encodeURIComponent(q.toLowerCase())}`)
}

/** The candidate's uploaded photo, or null when there is none (or no profile yet). */
export async function getPhoto(): Promise<Blob | null> {
  try {
    return await (await request('/me/photo')).blob()
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) return null
    throw error
  }
}

/** Needs a saved profile first (404 otherwise). The photo must already be a small JPEG (see squareJpeg). */
export async function uploadPhoto(photo: Blob): Promise<void> {
  const body = new FormData()
  body.append('file', photo, 'photo.jpg')
  await request('/me/photo', { method: 'PUT', body })
}

/** Back to the Google photo. */
export async function deletePhoto(): Promise<void> {
  await request('/me/photo', { method: 'DELETE' })
}

export type ChatMessage = { role: 'user' | 'assistant'; content: string }

/** The profile form as the assistant sees it (the backend ignores anything else). */
export type AssistantDraft = {
  full_name: string
  phone: string
  governorate_code: string
  education_level: string
  skills: { code: string; label_fr: string; level: number }[]
  experiences: {
    job_title_raw: string
    employer_name: string
    start_date: string
    end_date: string
    duration_months: string
  }[]
  desired_occupations: OccupationOption[]
  languages: { code: string; level: string }[]
  summary: string
}

/** Fields to merge into the profile form, in its own shape; null = unchanged. */
export type AssistantUpdates = {
  full_name: string | null
  phone: string | null
  governorate_code: string | null
  education_level: string | null
  skills: CvDraft['skills'] | null
  experiences: CvDraft['experiences'] | null
  desired_occupations: OccupationOption[] | null
  languages: { code: string; level: string }[] | null
  summary: string | null
}

export type AssistantReply = {
  reply: string
  updates: AssistantUpdates
  /** Skills and jobs the candidate named that aren't in our lists: the reply stays on them. */
  unmatched: string[]
  /** Close items of our lists the candidate can pick instead (labels). */
  suggestions: string[]
  /** The form field the reply asks about, so the form can show its step. */
  asking: keyof AssistantUpdates | null
  /** The assistant thinks the profile is complete (or the candidate said they're done). */
  done: boolean
}

/** The backend only sends the last 8 messages to the AI; no need to send more. */
const ASSISTANT_HISTORY = 8

/** One turn of the profile assistant. Nothing is saved: the updates are for the form. */
export function askAssistant(messages: ChatMessage[], draft: AssistantDraft): Promise<AssistantReply> {
  return api<AssistantReply>('/me/assistant/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ messages: messages.slice(-ASSISTANT_HISTORY), draft }),
  })
}

/** A profile draft read from a CV, in the profile form's shape ('' = not found). Nothing is saved yet. */
export type CvDraft = {
  full_name: string
  email: string
  phone: string
  education_level: string
  skills: Omit<ProfileSkill, 'skill_type'>[]
  experiences: {
    job_title_raw: string
    employer_name: string
    start_date: string
    end_date: string
    duration_months: string
    description: string
  }[]
  educations: Omit<Education, 'id'>[]
}
export type CvImport = { draft: CvDraft; unmatched_words: string[] }

export const MAX_CV_BYTES = 5 * 1024 * 1024

/**
 * Sends a PDF or DOCX CV and returns the draft read from it. The file isn't kept and nothing is saved.
 * Uses XMLHttpRequest because fetch can't report upload progress (`onProgress` gets 0..1).
 */
export async function importCv(file: File, onProgress: (sent: number) => void): Promise<CvImport> {
  const { data } = await supabase.auth.getSession()
  const body = new FormData()
  body.append('file', file)
  const xhr = new XMLHttpRequest()
  await new Promise<void>((resolve, reject) => {
    xhr.open('POST', `${API_BASE_URL}/api/v1/me/cv`)
    if (data.session) xhr.setRequestHeader('Authorization', `Bearer ${data.session.access_token}`)
    xhr.responseType = 'json'
    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) onProgress(event.loaded / event.total)
    }
    xhr.onload = () => resolve()
    xhr.onerror = () => reject(new Error('network error'))
    xhr.send(body)
  })
  if (xhr.status === 401) await supabase.auth.signOut({ scope: 'local' })
  if (xhr.status < 200 || xhr.status >= 300) throw new ApiError(xhr.status, xhr.response?.detail ?? null)
  return xhr.response
}
