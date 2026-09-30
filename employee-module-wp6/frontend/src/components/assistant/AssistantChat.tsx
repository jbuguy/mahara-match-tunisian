import {
  CircleAlert,
  CircleCheck,
  ClipboardCheck,
  LoaderCircle,
  MessageCircle,
  Mic,
  RotateCcw,
  SendHorizontal,
  SkipForward,
  X,
} from 'lucide-react'
import { useEffect, useRef, useState, type FormEvent } from 'react'

import { inputClass } from '@/components/profile/field-attrs'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { IGNORE, type AssistantChatState, type ChatEntry } from './use-assistant-chat'
import { useVoiceRecorder, type VoiceState } from './use-voice-recorder'

const MAX_MESSAGE = 1000 // the backend's limit for one message (a minute of speech fits)

/**
 * The "Assistant Mahara" chat: messages, a text box and Send. Used in the side panel (large screens) and in
 * the bottom sheet (phones); the conversation itself lives in the page (useAssistantChat).
 */
export function AssistantChat({
  chat,
  onClose,
  onReview,
  autoFocus = false,
}: {
  chat: AssistantChatState
  onClose: () => void
  /** "Vérifier mon profil": close the chat and go to the form. */
  onReview: () => void
  autoFocus?: boolean
}) {
  const [text, setText] = useState('')
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const logRef = useRef<HTMLDivElement>(null)
  const focusAfterTranscript = useRef(false)
  // A voice answer lands in the text box (after what's already typed), never sent by itself: the candidate
  // checks it, fixes it if needed, and presses "Envoyer".
  const voice = useVoiceRecorder((spoken) => {
    setText((current) => (current.trim() ? `${current.trimEnd()} ${spoken}` : spoken).slice(0, MAX_MESSAGE))
    focusAfterTranscript.current = autoFocus // large screens: ready to fix or press Enter (phones: no keyboard)
  })
  const voiceBusy = voice.state.status === 'recording' || voice.state.status === 'transcribing'

  useEffect(() => {
    if (autoFocus) inputRef.current?.focus()
  }, [autoFocus])

  // After a transcript on a large screen: focus the text box (back in place of the status line), cursor at the end.
  useEffect(() => {
    if (voiceBusy || !focusAfterTranscript.current) return
    focusAfterTranscript.current = false
    const input = inputRef.current
    input?.focus()
    input?.setSelectionRange(input.value.length, input.value.length)
  }, [voiceBusy])

  // Keep the newest message in view.
  useEffect(() => {
    const log = logRef.current
    log?.scrollTo({ top: log.scrollHeight, behavior: 'smooth' })
  }, [chat.entries.length, chat.waiting, chat.done])

  function submit(event?: FormEvent) {
    event?.preventDefault()
    const message = text.trim()
    if (!message || chat.waiting || voiceBusy) return
    chat.send(message)
    setText('')
    voice.clearError()
    inputRef.current?.focus()
  }

  return (
    <div className="flex h-full min-h-0 flex-col overflow-hidden bg-page">
      <header className="flex shrink-0 items-center justify-between gap-3 border-b bg-surface py-2 pr-2 pl-4">
        <div className="flex min-w-0 items-center gap-3">
          <span className="flex size-10 shrink-0 items-center justify-center rounded-full bg-teal text-white">
            <MessageCircle aria-hidden className="size-5" />
          </span>
          <div className="min-w-0">
            <h2 className="truncate text-lg text-ink">Assistant Mahara</h2>
            <p className="text-[13px] text-ink-secondary">Français, derja ou arabe</p>
          </div>
        </div>
        <Button variant="ghost" onClick={onClose} aria-label="Fermer l'assistant" className="text-ink-secondary">
          <X aria-hidden />
          Fermer
        </Button>
      </header>

      <div
        ref={logRef}
        role="log"
        aria-label="Conversation avec l'assistant"
        tabIndex={-1}
        className="min-h-0 flex-1 space-y-3 overflow-y-auto px-4 py-4 outline-none"
      >
        {chat.entries.map((entry, index) => (
          <Entry
            key={entry.id}
            entry={entry}
            latest={index === chat.entries.length - 1}
            waiting={chat.waiting}
            onRetry={chat.retry}
            onChoose={chat.send}
          />
        ))}
        {chat.waiting && <Typing />}
        {chat.done && !chat.waiting && (
          <Button size="lg" className="w-full" onClick={onReview}>
            <ClipboardCheck aria-hidden />
            Vérifier mon profil
          </Button>
        )}
      </div>

      <div className="shrink-0 space-y-2 border-t bg-surface p-3 pb-[max(0.75rem,env(safe-area-inset-bottom))]">
        {voice.error && (
          <p role="alert" className="flex items-start gap-1.5 text-[14px] text-danger">
            <CircleAlert aria-hidden className="mt-0.5 size-4 shrink-0" />
            {voice.error}
          </p>
        )}
        <form onSubmit={submit} className="space-y-2">
          <label htmlFor="assistant-message" className="sr-only">
            Votre réponse
          </label>
          {/* Full width and growing up to ~4 lines, so a spoken answer can be read in full and fixed. Enter sends. */}
          <textarea
            ref={inputRef}
            id="assistant-message"
            rows={1}
            dir="auto"
            autoComplete="off"
            enterKeyHint="send"
            maxLength={MAX_MESSAGE}
            placeholder="Écrivez votre réponse…" // the box sizes to it too: keep it on one line
            value={text}
            onChange={(event) => {
              setText(event.target.value)
              voice.clearError()
            }}
            onKeyDown={(event) => {
              if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
                event.preventDefault()
                submit()
              }
            }}
            className={cn(inputClass, 'field-sizing-content h-auto max-h-32 min-h-11 resize-none py-2.5 leading-snug')}
          />
          <div className="flex items-center justify-end gap-2">
            {voiceBusy && (
              <p role="status" className="flex min-w-0 flex-1 items-center gap-2 text-[15px] text-ink">
                {voice.state.status === 'transcribing' ? (
                  <>
                    <LoaderCircle aria-hidden className="size-5 shrink-0 animate-spin text-teal" />
                    <span className="truncate">Transcription…</span>
                  </>
                ) : (
                  <span className="truncate">
                    Parlez… <span className="text-ink-secondary">(1 min max)</span>
                  </span>
                )}
              </p>
            )}
            {voice.state.status === 'recording' && (
              <Button type="button" variant="ghost" onClick={voice.cancel} className="shrink-0 px-3">
                Annuler
              </Button>
            )}
            <MicButton state={voice.state} onStart={() => void voice.start()} onStop={voice.stop} />
            {!voiceBusy && (
              <Button type="submit" className="shrink-0" disabled={chat.waiting || !text.trim()}>
                <SendHorizontal aria-hidden />
                Envoyer
              </Button>
            )}
          </div>
        </form>
      </div>
    </div>
  )
}

/** "Parler": starts recording; while recording it's red with a pulsing dot and the time, and stops it. */
function MicButton({ state, onStart, onStop }: { state: VoiceState; onStart: () => void; onStop: () => void }) {
  if (state.status === 'recording') {
    const minutes = Math.floor(state.seconds / 60)
    const seconds = String(state.seconds % 60).padStart(2, '0')
    return (
      <Button
        type="button"
        onClick={onStop}
        aria-label={`Arrêter l'enregistrement (${minutes} min ${seconds} s)`}
        className="h-11 shrink-0 gap-2 bg-danger px-3.5 text-white hover:bg-danger/90"
      >
        <span aria-hidden className="size-2.5 animate-pulse rounded-full bg-white" />
        <span aria-hidden className="tabular-nums">
          {minutes}:{seconds}
        </span>
      </Button>
    )
  }
  return (
    <Button
      type="button"
      variant="outline"
      aria-label="Parler"
      disabled={state.status !== 'idle'}
      onClick={onStart}
      className="shrink-0 text-teal"
    >
      <Mic aria-hidden />
      Parler
    </Button>
  )
}

function Entry({
  entry,
  latest,
  waiting,
  onRetry,
  onChoose,
}: {
  entry: ChatEntry
  /** The newest entry: only its one-tap answers are shown. */
  latest: boolean
  waiting: boolean
  onRetry: () => void
  onChoose: (answer: string) => void
}) {
  if (entry.kind === 'error') {
    return (
      <div role="alert" className="space-y-2 rounded-[10px] border border-danger/40 bg-surface px-3 py-2.5">
        <p className="flex items-start gap-2 text-[14px] text-danger">
          <CircleAlert aria-hidden className="mt-0.5 size-4 shrink-0" />
          {entry.text}
        </p>
        <Button variant="outline" onClick={onRetry} disabled={waiting}>
          <RotateCcw aria-hidden />
          Réessayer
        </Button>
      </div>
    )
  }

  const mine = entry.role === 'user'
  return (
    <div className={cn('flex flex-col gap-1', mine ? 'items-end' : 'items-start')}>
      <p
        dir="auto"
        className={cn(
          'max-w-[85%] rounded-2xl px-3.5 py-2.5 text-[15px] leading-relaxed whitespace-pre-wrap',
          mine ? 'rounded-br-md bg-teal text-white' : 'rounded-bl-md border border-line bg-surface text-ink',
        )}
      >
        <span className="sr-only">{mine ? 'Vous : ' : 'Assistant : '}</span>
        {entry.content}
      </p>
      {entry.filled && entry.filled.length > 0 && (
        <p className="flex items-center gap-1 px-1 text-[13px] text-teal">
          <CircleCheck aria-hidden className="size-3.5 shrink-0" />
          Rempli : {entry.filled.join(', ')}
        </p>
      )}
      {latest && entry.choices && entry.choices.length > 0 && (
        <div role="group" aria-label="Réponses rapides" className="flex max-w-[85%] flex-wrap gap-2 pt-1">
          {entry.choices.map((choice) => (
            <Button
              key={choice}
              variant="outline"
              disabled={waiting}
              onClick={() => onChoose(choice)}
              className={cn(
                'h-auto min-h-11 rounded-full py-2 whitespace-normal',
                choice === IGNORE ? 'text-ink-secondary' : 'border-teal/40 text-teal',
              )}
            >
              {choice === IGNORE && <SkipForward aria-hidden />}
              {choice}
            </Button>
          ))}
        </div>
      )}
    </div>
  )
}

/** "..." while the assistant answers. */
function Typing() {
  return (
    <div className="flex justify-start">
      <div role="status" className="flex items-center gap-1 rounded-2xl rounded-bl-md border border-line bg-surface px-4 py-3.5">
        <span className="sr-only">L'assistant écrit…</span>
        {[0, 1, 2].map((dot) => (
          <span
            key={dot}
            aria-hidden
            className="size-2 animate-bounce rounded-full bg-ink-secondary/60"
            style={{ animationDelay: `${dot * 0.15}s` }}
          />
        ))}
      </div>
    </div>
  )
}
