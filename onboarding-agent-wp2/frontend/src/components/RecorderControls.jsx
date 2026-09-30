import { useRef, useState } from 'react'

const MIME_TYPES = [
  'audio/webm;codecs=opus',
  'audio/webm',
  'audio/ogg;codecs=opus',
  'audio/ogg',
  'audio/mp4',
]
const MIN_RECORDING_MS = 1000

function microphoneError(error) {
  if (error?.name === 'NotAllowedError' || error?.name === 'PermissionDeniedError') {
    return "L'accès au microphone est refusé. Autorisez-le dans le navigateur ou envoyez un fichier audio."
  }
  if (error?.name === 'NotFoundError' || error?.name === 'DevicesNotFoundError') {
    return "Aucun microphone n'a été détecté. Envoyez un fichier audio pour continuer."
  }
  return "Impossible d'accéder au microphone. Vérifiez ses branchements ou envoyez un fichier audio."
}

export default function RecorderControls({ onRecorded, disabled = false, retryAvailable = false, onRetry }) {
  const [recording, setRecording] = useState(false)
  const [error, setError] = useState('')
  const recorderRef = useRef(null)
  const streamRef = useRef(null)
  const chunksRef = useRef([])
  const startedAtRef = useRef(0)
  const fileInputRef = useRef(null)

  function releaseMicrophone() {
    streamRef.current?.getTracks().forEach((track) => track.stop())
    streamRef.current = null
  }

  async function startRecording() {
    setError('')
    onRetry?.()
    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
      setError("L'enregistrement n'est pas disponible dans ce navigateur. Envoyez un fichier audio.")
      return
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      streamRef.current = stream
      const mimeType = MIME_TYPES.find((type) => MediaRecorder.isTypeSupported?.(type))
      const recorder = mimeType
        ? new MediaRecorder(stream, { mimeType })
        : new MediaRecorder(stream)
      chunksRef.current = []
      recorderRef.current = recorder
      startedAtRef.current = Date.now()
      recorder.ondataavailable = (event) => {
        if (event.data?.size) chunksRef.current.push(event.data)
      }
      recorder.onerror = () => {
        setError("L'enregistrement a échoué. Réessayez ou envoyez un fichier audio.")
        setRecording(false)
        releaseMicrophone()
      }
      recorder.onstop = () => {
        const duration = Date.now() - startedAtRef.current
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType || mimeType || 'audio/webm' })
        setRecording(false)
        releaseMicrophone()
        if (duration < MIN_RECORDING_MS || !blob.size) {
          setError("L'enregistrement est trop court. Parlez au moins une seconde puis réessayez.")
          return
        }
        onRecorded(blob)
      }
      recorder.start()
      setRecording(true)
    } catch (cause) {
      releaseMicrophone()
      setError(microphoneError(cause))
    }
  }

  function stopRecording() {
    if (recorderRef.current?.state === 'recording') recorderRef.current.stop()
  }

  function handleFile(event) {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file) return
    setError('')
    if (!file.size) {
      setError('Le fichier audio est vide. Choisissez un autre fichier puis réessayez.')
      return
    }
    onRecorded(file)
  }

  return (
    <div className="recording-controls">
      <div className="recording-actions">
        <button
          className={recording ? 'button button-recording' : 'button button-primary'}
          type="button"
          onClick={recording ? stopRecording : startRecording}
          disabled={disabled}
        >
          {recording && <span className="recording-dot" aria-hidden="true" />}
          {recording ? 'Arrêter' : retryAvailable ? 'Réessayer' : 'Enregistrer'}
        </button>
        <button
          className="button button-secondary"
          type="button"
          onClick={() => fileInputRef.current?.click()}
          disabled={disabled || recording}
        >
          Envoyer un fichier audio
        </button>
        <input
          ref={fileInputRef}
          className="visually-hidden"
          type="file"
          accept="audio/*"
          aria-label="Choisir un fichier audio"
          onChange={handleFile}
          disabled={disabled || recording}
        />
      </div>
      {recording && <p className="recording-status" role="status">Enregistrement en cours</p>}
      {error && <p className="message message-error" role="alert">{error}</p>}
    </div>
  )
}