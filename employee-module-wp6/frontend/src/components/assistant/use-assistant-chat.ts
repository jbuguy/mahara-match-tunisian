import { useState, type RefObject } from 'react'

import type { ProfileFormHandle } from '@/components/profile/ProfileForm'
import { changedLabels, toAssistantDraft } from '@/components/profile/assistant-updates'
import { ApiError, askAssistant, type ChatMessage } from '@/lib/api'

export const GREETING =
  'Ahla ! Je vais vous aider à compléter votre profil. Vous pouvez répondre en français ou en derja. ' +
  'Comment vous appelez-vous ?'

/** The one-tap answer that skips a skill or job that isn't in our lists (the assistant understands it). */
export const IGNORE = 'Ignorer'

export type ChatEntry =
  /**
   * `filled`: French names of the form parts this reply filled ("Nom complet", "Compétences").
   * `choices`: one-tap answers offered under the reply (close items of our lists, then "Ignorer").
   */
  | { id: number; kind: 'message'; role: ChatMessage['role']; content: string; filled?: string[]; choices?: string[] }
  /** The last request failed; the candidate can try again. Never sent to the AI. */
  | { id: number; kind: 'error'; text: string }

let lastId = 0
function nextId(): number {
  lastId += 1
  return lastId
}

function errorText(error: unknown): string {
  if (!(error instanceof ApiError)) return 'Connexion impossible. Vérifiez votre connexion et réessayez.'
  // The backend explains 429 / 502 / 503 in French ("Un instant, réessayez dans quelques secondes.").
  if ([429, 502, 503].includes(error.status) && typeof error.detail === 'string') return error.detail
  return "Désolé, l'assistant n'a pas pu répondre. Réessayez, ou remplissez le formulaire vous-même."
}

function withoutErrors(entries: ChatEntry[]): ChatEntry[] {
  return entries.filter((entry) => entry.kind !== 'error')
}

/**
 * The conversation with the profile assistant, kept in React state only (lost on refresh).
 * Each reply's updates go straight into the form through its handle; nothing is saved.
 */
export function useAssistantChat(form: RefObject<ProfileFormHandle | null>) {
  const [entries, setEntries] = useState<ChatEntry[]>(() => [
    { id: nextId(), kind: 'message', role: 'assistant', content: GREETING },
  ])
  const [waiting, setWaiting] = useState(false)
  const [done, setDone] = useState(false)

  async function ask(conversation: ChatEntry[]) {
    const handle = form.current
    if (!handle) return
    setWaiting(true)
    const messages = conversation.flatMap((entry) =>
      entry.kind === 'message' ? [{ role: entry.role, content: entry.content }] : [],
    )
    try {
      const answer = await askAssistant(messages, toAssistantDraft(handle.getValues()))
      const filled = changedLabels(form.current?.applyUpdates(answer.updates, answer.asking) ?? [])
      // Something isn't in our lists: the reply stays on it until the candidate picks, rewrites or skips it.
      const choices = answer.unmatched.length > 0 ? [...answer.suggestions, IGNORE] : undefined
      setEntries((current) => [
        ...current,
        { id: nextId(), kind: 'message', role: 'assistant', content: answer.reply, filled, choices },
      ])
      setDone(answer.done)
    } catch (error) {
      setEntries((current) => [...current, { id: nextId(), kind: 'error', text: errorText(error) }])
    } finally {
      setWaiting(false)
    }
  }

  function send(text: string) {
    if (waiting) return
    const next: ChatEntry[] = [...withoutErrors(entries), { id: nextId(), kind: 'message', role: 'user', content: text }]
    setEntries(next)
    void ask(next)
  }

  /** Sends the same conversation again after an error. */
  function retry() {
    if (waiting) return
    const next = withoutErrors(entries)
    setEntries(next)
    void ask(next)
  }

  return { entries, waiting, done, send, retry }
}

export type AssistantChatState = ReturnType<typeof useAssistantChat>
