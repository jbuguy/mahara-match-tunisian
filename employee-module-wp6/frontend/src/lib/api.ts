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
