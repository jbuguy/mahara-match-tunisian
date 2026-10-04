import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { API_BASE_URL, requestJson } from '../lib/api'

type Question = { id: string; texte: string; audio_url: string }
type Governorate = { code: string; name_fr: string; name_ar: string }
type OnboardingSession = {
  session_id: string
  termine: boolean
  question: Question | null
  answers: Record<string, string>
}
type SessionCreated = { session_id: string; question: Question }
type AnswerResult = {
  texte_brut: string
  valeur_extraite: string | null
  question_suivante: Question | null
  termine: boolean
}

const SESSION_KEY = 'mahara_wp2_session_id'
const QUESTION_COUNT = 4
const MIME_TYPES = ['audio/webm;codecs=opus', 'audio/webm', 'audio/ogg;codecs=opus', 'audio/ogg', 'audio/mp4']

function normalizePlace(value: string) {
  return value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').trim().toLocaleLowerCase()
}

export function OnboardingPage() {
  const navigate = useNavigate()
  const recorderRef = useRef<MediaRecorder | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const startedAtRef = useRef(0)
  const cancelRecordingRef = useRef(false)
  const [sessionId, setSessionId] = useState('')
  const [question, setQuestion] = useState<Question | null>(null)
  const [answers, setAnswers] = useState<Record<string, string>>({})
  const [governorates, setGovernorates] = useState<Governorate[]>([])
  const [recording, setRecording] = useState(false)
  const [busy, setBusy] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [lastTranscript, setLastTranscript] = useState('')
  const [reviewJob, setReviewJob] = useState('')
  const [reviewDate, setReviewDate] = useState('')
  const [reviewGovernorate, setReviewGovernorate] = useState('')
  const [reviewPhone, setReviewPhone] = useState('')
  const tokenPresent = Boolean(localStorage.getItem('mahara_access_token'))
  const completed = !question && sessionId.length > 0 && Object.keys(answers).length > 0
  const questionNumber = question ? ['metier', 'date', 'gouvernorat', 'telephone'].indexOf(question.id) + 1 : 0

  useEffect(() => {
    if (!tokenPresent) {
      setLoading(false)
      return
    }

    let active = true
    async function restore() {
      try {
        const places = await requestJson<Governorate[]>('/api/v1/reference/governorates')
        if (active) setGovernorates(places)
      } catch {
        if (active) setError('Governorate options could not be loaded. You can still complete the voice questions.')
      }

      const savedSessionId = localStorage.getItem(SESSION_KEY)
      if (savedSessionId) {
        try {
          const session = await requestJson<OnboardingSession>(`/api/v1/onboarding/sessions/${encodeURIComponent(savedSessionId)}`)
          if (!active) return
          setSessionId(session.session_id)
          setQuestion(session.question)
          if (session.termine) setAnswers(session.answers)
        } catch {
          localStorage.removeItem(SESSION_KEY)
        }
      }
      if (active) setLoading(false)
    }

    void restore()
    return () => { active = false }
  }, [tokenPresent])

  useEffect(() => () => {
    cancelRecordingRef.current = true
    if (recorderRef.current?.state === 'recording') recorderRef.current.stop()
    streamRef.current?.getTracks().forEach((track) => track.stop())
  }, [])

  useEffect(() => {
    const rawPlace = answers.gouvernorat
    if (!rawPlace || reviewGovernorate || governorates.length === 0) return
    const normalized = normalizePlace(rawPlace)
    const match = governorates.find((place) =>
      normalizePlace(place.name_fr) === normalized || normalizePlace(place.name_ar) === normalized,
    )
    if (match) setReviewGovernorate(match.code)
  }, [answers.gouvernorat, governorates, reviewGovernorate])

  useEffect(() => {
    if (!completed) return
    setReviewJob(answers.metier ?? '')
    setReviewDate('')
    setReviewPhone(answers.telephone ?? '')
  }, [completed, answers])

  async function beginSession() {
    setBusy(true)
    setError('')
    try {
      const created = await requestJson<SessionCreated>('/api/v1/onboarding/sessions', { method: 'POST' })
      localStorage.setItem(SESSION_KEY, created.session_id)
      setSessionId(created.session_id)
      setQuestion(created.question)
      setAnswers({})
      setNotice('')
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not start onboarding.')
    } finally {
      setBusy(false)
    }
  }

  async function submitRecording(blob: Blob) {
    if (!sessionId || !question) return
    setBusy(true)
    setError('')
    setNotice('Transcribing your response…')
    try {
      const body = new FormData()
      const subtype = blob.type.split(';')[0].split('/')[1]
      const extension = subtype === 'mp4' ? 'm4a' : subtype || 'webm'
      body.append('audio', blob, `answer.${extension}`)
      const result = await requestJson<AnswerResult>(
        `/api/v1/onboarding/sessions/${encodeURIComponent(sessionId)}/reponse`,
        { method: 'POST', body },
      )
      setLastTranscript(result.texte_brut)
      setNotice(result.valeur_extraite ? `Recognized answer: ${result.valeur_extraite}` : 'Response recognized. Review it when the questions are complete.')
      if (result.termine) {
        const completedSession = await requestJson<OnboardingSession>(`/api/v1/onboarding/sessions/${encodeURIComponent(sessionId)}`)
        setAnswers(completedSession.answers)
        setQuestion(null)
      } else {
        setQuestion(result.question_suivante)
      }
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not submit this recording.')
      setNotice('')
    } finally {
      setBusy(false)
    }
  }

  async function startRecording() {
    setError('')
    setNotice('')
    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
      setError('Voice recording is unavailable in this browser. Open the app in a supported browser over HTTPS or localhost.')
      return
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      streamRef.current = stream
      const mimeType = MIME_TYPES.find((candidate) => MediaRecorder.isTypeSupported?.(candidate))
      const recorder = mimeType ? new MediaRecorder(stream, { mimeType }) : new MediaRecorder(stream)
      chunksRef.current = []
      cancelRecordingRef.current = false
      startedAtRef.current = Date.now()
      recorderRef.current = recorder
      recorder.ondataavailable = (event) => {
        if (event.data.size) chunksRef.current.push(event.data)
      }
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
        if (cancelRecordingRef.current) return
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType || mimeType || 'audio/webm' })
        if (Date.now() - startedAtRef.current < 700 || !blob.size) {
          setError('That recording was too short. Record your answer again.')
          return
        }
        void submitRecording(blob)
      }
      recorder.start()
      setRecording(true)
    } catch (cause) {
      streamRef.current?.getTracks().forEach((track) => track.stop())
      streamRef.current = null
      const name = cause instanceof DOMException ? cause.name : ''
      setError(name === 'NotAllowedError'
        ? 'Microphone permission was denied. Allow microphone access and try again.'
        : name === 'NotFoundError'
          ? 'No microphone was found on this device.'
          : 'Could not access the microphone. Check your browser permissions and try again.')
    }
  }

  function stopRecording() {
    if (recorderRef.current?.state === 'recording') recorderRef.current.stop()
  }

  function continueToProfile() {
    localStorage.removeItem(SESSION_KEY)
    navigate('/candidate', {
      state: {
        wp2Draft: {
          jobTitle: reviewJob.trim(),
          availableFrom: reviewDate || null,
          governorateCode: reviewGovernorate || null,
          phone: reviewPhone.trim() || null,
        },
      },
    })
  }

  if (!tokenPresent) {
    return (
      <div className="stacked-view">
        <h2>Candidate onboarding</h2>
        <p>Sign in to start a voice onboarding session.</p>
        <Link className="primary-btn" to="/signin">Sign in</Link>
      </div>
    )
  }

  return (
    <div className="stacked-view">
      <header className="panel-header">
        <div><p className="eyebrow">WP2 · Candidate</p><h2>Voice onboarding</h2></div>
        {question && <span className="module-tag">Question {questionNumber} of {QUESTION_COUNT}</span>}
      </header>

      <section className="agent-panel onboarding-panel">
        {loading ? <p role="status">Loading your onboarding session…</p> : null}
        {!loading && !sessionId && (
          <div className="onboarding-start">
            <p>Answer four short questions by voice. Your answers are reviewed before they are added to your profile.</p>
            <button className="primary-btn" type="button" onClick={beginSession} disabled={busy}>Start voice onboarding</button>
          </div>
        )}

        {!loading && question && (
          <>
            <div className="question-box">
              <span>Prompt {questionNumber}</span>
              <p>{question.texte}</p>
            </div>
            <audio className="question-audio" controls preload="none" src={`${API_BASE_URL}${question.audio_url}`}>
              Audio playback is not supported in this browser.
            </audio>
            <div className="voice-actions">
              <button
                className={recording ? 'primary-btn voice-recording' : 'primary-btn'}
                type="button"
                onClick={recording ? stopRecording : startRecording}
                disabled={busy}
              >
                <span className="voice-indicator" aria-hidden="true" />
                {recording ? 'Stop recording' : busy ? 'Processing…' : 'Record answer'}
              </button>
              {recording && <span role="status">Recording. Speak clearly, then stop.</span>}
            </div>
          </>
        )}

        {completed && (
          <>
            <div className="question-box">
              <span>Review your answers</span>
              <p>Check the extracted details, then continue to your candidate profile. Nothing is saved to your profile until you review it there and give consent.</p>
            </div>
            <div className="auth-form onboarding-review">
              <label><span>Profession or trade</span><input value={reviewJob} onChange={(event) => setReviewJob(event.target.value)} /></label>
              <label>
                <span>Availability date</span>
                <input type="date" value={reviewDate} onChange={(event) => setReviewDate(event.target.value)} />
                {answers.date_disponibilite && <small>Voice answer: {answers.date_disponibilite}. Select the calendar date to use in your profile.</small>}
              </label>
              <label><span>Governorate</span><select value={reviewGovernorate} onChange={(event) => setReviewGovernorate(event.target.value)}><option value="">Select a governorate</option>{governorates.map((place) => <option key={place.code} value={place.code}>{place.name_fr}</option>)}</select></label>
              <label><span>Phone</span><input type="tel" value={reviewPhone} onChange={(event) => setReviewPhone(event.target.value)} /></label>
            </div>
            <button className="primary-btn" type="button" onClick={continueToProfile}>Continue to candidate profile</button>
          </>
        )}

        {lastTranscript && !completed && <p className="form-notice" aria-live="polite">Last recognized response: {lastTranscript}</p>}
        {notice && <p className="form-notice" aria-live="polite">{notice}</p>}
        {error && <p className="form-error" role="alert">{error}</p>}
      </section>
    </div>
  )
}
