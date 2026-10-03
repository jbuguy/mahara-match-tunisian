/**
 * Which photo to show for the signed-in user: their uploaded photo if they have one, otherwise the
 * Google photo from the login. Shared by the top bar, the sidebar, the Profil page and the form.
 */

import { useEffect, useSyncExternalStore } from 'react'
import type { Session } from '@supabase/supabase-js'

import { getPhoto } from './api'
import { useAuth } from './auth-context'

type PhotoState = {
  userId: string | null
  loading: boolean
  /** Object URL of the uploaded photo, or null when there is none. */
  custom: string | null
}

let state: PhotoState = { userId: null, loading: false, custom: null }
const listeners = new Set<() => void>()

function update(next: PhotoState) {
  if (state.custom && state.custom !== next.custom) URL.revokeObjectURL(state.custom)
  state = next
  listeners.forEach((listener) => listener())
}

function subscribe(listener: () => void) {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

// Remembers whether this user has an uploaded photo, so the Google photo doesn't flash before it on reload.
const hintKey = (userId: string) => `mahara-custom-photo:${userId}`

function readHint(userId: string): boolean {
  try {
    return localStorage.getItem(hintKey(userId)) === '1'
  } catch {
    return false
  }
}

function writeHint(userId: string, hasCustom: boolean) {
  try {
    if (hasCustom) localStorage.setItem(hintKey(userId), '1')
    else localStorage.removeItem(hintKey(userId))
  } catch {
    // Storage blocked: only the hint is lost.
  }
}

function load(userId: string) {
  if (state.userId === userId) return
  update({ userId, loading: true, custom: null })
  getPhoto()
    .then((blob) => {
      if (state.userId !== userId) return
      writeHint(userId, blob !== null)
      update({ userId, loading: false, custom: blob ? URL.createObjectURL(blob) : null })
    })
    .catch(() => {
      if (state.userId === userId) update({ userId, loading: false, custom: null })
    })
}

/** After an upload (a Blob) or a removal (null): show it everywhere without asking the server again. */
export function setCustomPhoto(photo: Blob | null) {
  if (state.userId) writeHint(state.userId, photo !== null)
  update({ ...state, loading: false, custom: photo ? URL.createObjectURL(photo) : null })
}

/** The Google photo from the login, asked at 256px (Google serves 96px by default). */
export function googlePhotoUrl(session: Session | null): string | null {
  const metadata = session?.user.user_metadata ?? {}
  const url: unknown = metadata.avatar_url || metadata.picture
  return typeof url === 'string' && url ? url.replace(/=s\d+-c$/, '=s256-c') : null
}

export type UserPhoto = {
  /** What to show; null means initials. */
  src: string | null
  hasCustom: boolean
  google: string | null
}

export function useUserPhoto(): UserPhoto {
  const { session } = useAuth()
  const userId = session?.user.id ?? null
  const current = useSyncExternalStore(subscribe, () => state)

  useEffect(() => {
    if (userId) load(userId)
  }, [userId])

  const google = googlePhotoUrl(session)
  const mine = current.userId === userId
  if (!mine || current.loading) {
    // Still asking the server: initials if we expect an uploaded photo, else the Google one straight away.
    return { src: userId && readHint(userId) ? null : google, hasCustom: false, google }
  }
  return { src: current.custom ?? google, hasCustom: current.custom !== null, google }
}
