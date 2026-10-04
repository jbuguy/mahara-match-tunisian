import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'

export function AuthCallbackPage() {
  const navigate = useNavigate()

  useEffect(() => {
    const hash = window.location.hash.startsWith('#') ? window.location.hash.slice(1) : window.location.hash
    const params = new URLSearchParams(hash)
    const accessToken = params.get('access_token')
    const error = new URLSearchParams(window.location.search).get('error')

    if (error) {
      navigate('/signin', { replace: true })
      return
    }

    if (accessToken) {
      localStorage.setItem('mahara_access_token', accessToken)
      navigate('/dashboard', { replace: true })
      return
    }

    navigate('/signin', { replace: true })
  }, [navigate])

  return (
    <div className="auth-card">
      <div className="auth-intro">
        <p className="eyebrow">Signing in</p>
        <h2>Completing your Google sign-in…</h2>
      </div>
    </div>
  )
}