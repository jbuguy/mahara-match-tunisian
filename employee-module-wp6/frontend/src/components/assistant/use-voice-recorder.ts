import { useEffect, useRef, useState } from 'react'

import { ApiError, MAX_AUDIO_BYTES, transcribeAudio } from '@/lib/api'

export const MAX_RECORDING_SECONDS = 60
const MIN_RECORDING_MS = 800 // shorter is a tap by mistake: Whisper would guess words from silence

// Formats the backend accepts, in the order we'd like them (MediaRecorder picks what the browser can do).
const AUDIO_TYPES = ['audio/webm;codecs=opus', 'audio/webm', 'audio/ogg;codecs=opus', 'audio/ogg', 'audio/mp4']

const MESSAGES = {
  denied: 'Autorisez le micro dans votre navigateur, puis réessayez. Vous pouvez aussi écrire votre réponse.',
  noMicrophone: 'Aucun micro trouvé. Écrivez votre réponse.',
  unsupported: "Votre navigateur ne permet pas d'enregistrer la voix. Écrivez votre réponse.",
  tooShort: 'Enregistrement trop court. Appuyez sur le micro, parlez, puis appuyez de nouveau.',
  tooLong: 'Enregistrement trop long. Parlez moins longtemps, ou écrivez votre réponse.',
  nothingHeard: "Nous n'avons rien entendu. Réessayez, ou écrivez votre réponse.",
  failed: 'La transcription a échoué. Réessayez, ou écrivez votre réponse.',
  offline: 'Connexion impossible. Vérifiez votre connexion et réessayez.',
}

export type VoiceState =
  | { status: 'idle' }
  | { status: 'starting' } // waiting for the microphone (the browser may ask for permission)
  | { status: 'recording'; seconds: number }
  | { status: 'transcribing' }

function isSupported(): boolean {
  return typeof MediaRecorder !== 'undefined' && Boolean(navigator.mediaDevices?.getUserMedia)
}

function transcriptionError(error: unknown): string {
  if (!(error instanceof ApiError)) return MESSAGES.offline
  if (error.status === 413) return MESSAGES.tooLong
  // 429 / 502 / 503 come with a French message from the backend ("Un instant, réessayez dans quelques secondes.").
  if ([429, 502, 503].includes(error.status) && typeof error.detail === 'string') return error.detail
  return MESSAGES.failed
}

/**
 * Records the candidate's voice with the browser's MediaRecorder (60 s at most) and turns it into text.
 * `onText` receives the transcript, which goes into the chat's text box: it is never sent on its own.
 * Nothing is stored; closing the chat while recording throws the recording away.
 */
export function useVoiceRecorder(onText: (text: string) => void) {
  const [state, setState] = useState<VoiceState>({ status: 'idle' })
  const [error, setError] = useState<string | null>(null)
  const recorderRef = useRef<MediaRecorder | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const timerRef = useRef<number | undefined>(undefined)
  const discardRef = useRef(false)
  const onTextRef = useRef(onText)
  useEffect(() => {
    onTextRef.current = onText
  }, [onText])

  function release() {
    window.clearInterval(timerRef.current)
    streamRef.current?.getTracks().forEach((track) => track.stop()) // turns the browser's "recording" light off
    streamRef.current = null
    recorderRef.current = null
  }

  // Leaving (the chat closes): stop and throw away any recording in progress.
  useEffect(
    () => () => {
      discardRef.current = true
      if (recorderRef.current?.state === 'recording') recorderRef.current.stop()
      window.clearInterval(timerRef.current)
      streamRef.current?.getTracks().forEach((track) => track.stop())
    },
    [],
  )

  async function start() {
    if (state.status !== 'idle') return
    setError(null)
    if (!isSupported()) return setError(MESSAGES.unsupported)

    setState({ status: 'starting' })
    let stream: MediaStream
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    } catch (reason) {
      setState({ status: 'idle' })
      const name = reason instanceof DOMException ? reason.name : ''
      if (name === 'NotAllowedError' || name === 'SecurityError') setError(MESSAGES.denied)
      else if (name === 'NotFoundError' || name === 'OverconstrainedError') setError(MESSAGES.noMicrophone)
      else setError(MESSAGES.unsupported)
      return
    }

    const mimeType = AUDIO_TYPES.find((type) => MediaRecorder.isTypeSupported(type))
    let recorder: MediaRecorder
    try {
      recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined)
    } catch {
      stream.getTracks().forEach((track) => track.stop())
      setState({ status: 'idle' })
      return setError(MESSAGES.unsupported)
    }
    const chunks: Blob[] = []
    const startedAt = Date.now()
    streamRef.current = stream
    recorderRef.current = recorder
    discardRef.current = false

    recorder.ondataavailable = (event) => {
      if (event.data.size > 0) chunks.push(event.data)
    }
    recorder.onstop = () => {
      const audio = new Blob(chunks, { type: recorder.mimeType || mimeType || 'audio/webm' })
      release()
      if (discardRef.current) return setState({ status: 'idle' })
      if (Date.now() - startedAt < MIN_RECORDING_MS) {
        setState({ status: 'idle' })
        return setError(MESSAGES.tooShort)
      }
      void send(audio)
    }

    recorder.start()
    setState({ status: 'recording', seconds: 0 })
    timerRef.current = window.setInterval(() => {
      const seconds = Math.floor((Date.now() - startedAt) / 1000)
      if (seconds >= MAX_RECORDING_SECONDS) stop()
      else setState({ status: 'recording', seconds })
    }, 250)
  }

  /** Stops recording and sends the audio for transcription. */
  function stop() {
    window.clearInterval(timerRef.current)
    if (recorderRef.current?.state === 'recording') recorderRef.current.stop()
  }

  /** "Annuler": stops and throws the recording away. */
  function cancel() {
    discardRef.current = true
    stop()
  }

  async function send(audio: Blob) {
    if (audio.size > MAX_AUDIO_BYTES) {
      setState({ status: 'idle' })
      return setError(MESSAGES.tooLong)
    }
    setState({ status: 'transcribing' })
    try {
      const text = (await transcribeAudio(audio)).trim()
      if (text) onTextRef.current(text)
      else setError(MESSAGES.nothingHeard)
    } catch (reason) {
      setError(transcriptionError(reason))
    } finally {
      setState({ status: 'idle' })
    }
  }

  return { state, error, clearError: () => setError(null), start, stop, cancel }
}
