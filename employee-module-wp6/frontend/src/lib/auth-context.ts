import { createContext, useContext } from 'react'
import type { Session } from '@supabase/supabase-js'

export type AuthState = {
  session: Session | null
  /** True until Supabase has restored the session (or finished the Google redirect). */
  loading: boolean
  signInWithGoogle: () => Promise<void>
  signOut: () => Promise<void>
}

export const AuthContext = createContext<AuthState | null>(null)

export function useAuth(): AuthState {
  const auth = useContext(AuthContext)
  if (!auth) throw new Error('useAuth must be used inside <AuthProvider>')
  return auth
}

/** Google gives the full name in user_metadata; fall back to the email. */
export function displayName(session: Session | null): string {
  const metadata = session?.user.user_metadata ?? {}
  return metadata.full_name || metadata.name || session?.user.email || ''
}

export function initials(name: string): string {
  const words = name.replace(/@.*/, '').split(/[\s._-]+/).filter(Boolean)
  if (words.length === 0) return '?'
  const letters = words.length > 1 ? words[0][0] + words[words.length - 1][0] : words[0][0]
  return letters.toUpperCase()
}
