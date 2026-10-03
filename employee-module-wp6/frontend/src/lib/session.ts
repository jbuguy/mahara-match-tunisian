export type Session = {
  access_token: string
  user: {
    id: string
    email: string
    user_metadata: { full_name?: string; name?: string; avatar_url?: string; picture?: string }
  }
}

const TOKEN_KEY = 'mahara-access-token'

function sessionFromToken(token: string): Session | null {
  try {
    const payload = token.split('.')[1]
    if (!payload) return null
    const base64 = payload.replace(/-/g, '+').replace(/_/g, '/')
    const decoded = window.atob(base64.padEnd(Math.ceil(base64.length / 4) * 4, '='))
    const bytes = Uint8Array.from(decoded, (character) => character.charCodeAt(0))
    const claims = JSON.parse(new TextDecoder().decode(bytes))
    if (
      typeof claims.sub !== 'string' ||
      typeof claims.email !== 'string' ||
      typeof claims.exp !== 'number' ||
      claims.exp <= Date.now() / 1000
    ) {
      return null
    }
    const name = typeof claims.name === 'string' ? claims.name : undefined
    const picture = typeof claims.picture === 'string' ? claims.picture : undefined
    return {
      access_token: token,
      user: {
        id: claims.sub,
        email: claims.email,
        user_metadata: { full_name: name, name, avatar_url: picture, picture },
      },
    }
  } catch {
    return null
  }
}

export function getAccessToken(): string | null {
  try {
    return sessionStorage.getItem(TOKEN_KEY)
  } catch {
    return null
  }
}

export function clearAuthSession() {
  try {
    sessionStorage.removeItem(TOKEN_KEY)
  } catch {
    // Storage can be disabled by the browser.
  }
}

export function restoreAuthSession(): Session | null {
  const fragment = new URLSearchParams(window.location.hash.slice(1))
  const returnedToken = fragment.get('access_token')
  if (window.location.hash) window.history.replaceState(null, '', window.location.pathname + window.location.search)

  const token = returnedToken ?? getAccessToken()
  if (!token) return null
  const session = sessionFromToken(token)
  if (!session) {
    clearAuthSession()
    return null
  }
  try {
    sessionStorage.setItem(TOKEN_KEY, token)
  } catch {
    return null
  }
  return session
}