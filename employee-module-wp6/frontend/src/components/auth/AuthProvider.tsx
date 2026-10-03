import { useEffect, useMemo, useState, type ReactNode } from 'react'

import { AuthContext, type AuthState } from '@/lib/auth-context'
import { clearAuthSession, restoreAuthSession, type Session } from '@/lib/session'

async function signInWithGoogle() {
  window.location.assign(`${import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8006'}/api/v1/auth/google`)
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
