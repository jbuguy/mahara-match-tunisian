import { useEffect, useMemo, useState, type ReactNode } from 'react'

import { AuthContext, type AuthState } from '@/lib/auth-context'
import { API_BASE_URL } from '@/lib/api'
import { clearAuthSession, restoreAuthSession, type Session } from '@/lib/session'

async function signInWithGoogle() {
  window.location.assign(`${API_BASE_URL}/api/v1/auth/google`)
}

async function signOut() {
  clearAuthSession()
  window.dispatchEvent(new Event('mahara:signout'))
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setSession(restoreAuthSession())
    setLoading(false)
    const onSignOut = () => setSession(null)
    window.addEventListener('mahara:signout', onSignOut)
    return () => window.removeEventListener('mahara:signout', onSignOut)
  }, [])

  const value = useMemo<AuthState>(() => ({ session, loading, signInWithGoogle, signOut }), [session, loading])
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
