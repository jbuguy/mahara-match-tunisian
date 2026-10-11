import { useEffect, useRef, useState } from 'react'

import { requestJson } from './api'

const MIME_TYPES = ['audio/webm;codecs=opus', 'audio/webm', 'audio/ogg;codecs=opus', 'audio/ogg', 'audio/mp4']
const MAX_RECORDING_SECONDS = 60

export function useVoiceInput(endpoint: string) {
  const [recording, setRecording] = useState(false)
  const [transcribing, setTranscribing] = useState(false)
  const [error, setError] = useState('')
  const [transcript, setTranscript] = useState('')
  const recorderRef = useRef<MediaRecorder | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const startedAtRef = useRef(0)
  const cancelledRef = useRef(false)
  const timeoutRef = useRef<number | undefined>(undefined)

  useEffect(() => () => {
    window.clearTimeout(timeoutRef.current)
    cancelledRef.current = true
    if (recorderRef.current?.state === 'recording') recorderRef.current.stop()
    streamRef.current?.getTracks().forEach((track) => track.stop())
  }, [])

  async function transcribe(blob: Blob) {
    setTranscribing(true)
    try {
      const body = new FormData()
      const subtype = blob.type.split(';')[0].split('/')[1]
      const extension = subtype === 'mp4' ? 'm4a' : subtype || 'webm'
      body.append('file', blob, `recording.${extension}`)
      const result = await requestJson<{ text: string }>(endpoint, { method: 'POST', body })
      if (!result.text) setError('No words were recognized. Try again or type your answer.')
      else setTranscript(result.text)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Transcription failed. Type your answer instead.')
    } finally {
      setTranscribing(false)
    }
  }

  async function start() {
    setError('')
    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
      setError('Voice recording is unavailable in this browser. You can type your answer instead.')
      return
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      streamRef.current = stream
      const mimeType = MIME_TYPES.find((candidate) => MediaRecorder.isTypeSupported?.(candidate))
      const recorder = mimeType ? new MediaRecorder(stream, { mimeType }) : new MediaRecorder(stream)
      chunksRef.current = []
      cancelledRef.current = false
      startedAtRef.current = Date.now()
      recorderRef.current = recorder
      recorder.ondataavailable = (event) => { if (event.data.size) chunksRef.current.push(event.data) }
      recorder.onerror = () => {
        setRecording(false)
        setError('Recording failed. Check microphone access and try again.')
        stream.getTracks().forEach((track) => track.stop())
        streamRef.current = null
      }
      recorder.onstop = () => {
        stream.getTracks().forEach((track) => track.stop())
        streamRef.current = null
        setRecording(false)
        if (cancelledRef.current) return
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType || mimeType || 'audio/webm' })
        if (Date.now() - startedAtRef.current < 800 || !blob.size) {
          setError('That recording was too short. Try again or type your answer.')
          return
        }
        void transcribe(blob)
      }
      recorder.start()
      setRecording(true)
      timeoutRef.current = window.setTimeout(() => {
        if (recorderRef.current?.state === 'recording') recorderRef.current.stop()
      }, MAX_RECORDING_SECONDS * 1000)
    } catch (cause) {
      streamRef.current?.getTracks().forEach((track) => track.stop())
      streamRef.current = null
      const name = cause instanceof DOMException ? cause.name : ''
      setError(name === 'NotAllowedError'
        ? 'Allow microphone access in your browser, then try again.'
        : name === 'NotFoundError'
          ? 'No microphone was found on this device.'
          : 'Could not access the microphone. You can type your answer instead.')
    }
  }

  function stop() {
    window.clearTimeout(timeoutRef.current)
    if (recorderRef.current?.state === 'recording') recorderRef.current.stop()
  }

  function clearTranscript() {
    setTranscript('')
  }

  return { recording, transcribing, error, transcript, start, stop, clearTranscript }
}