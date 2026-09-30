import { useEffect, useRef, useState } from 'react'
import { envoyerReponse } from '../api.js'
import RecorderControls from './RecorderControls.jsx'

const QUESTION_ORDER = ['metier', 'date', 'gouvernorat', 'telephone']

export default function QuestionScreen({ sessionId, question, onNext, onFinish }) {
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [audioNotice, setAudioNotice] = useState('')
  const audioRef = useRef(null)
  const questionNumber = QUESTION_ORDER.indexOf(question.id) + 1
  const progress = `${(questionNumber / QUESTION_ORDER.length) * 100}%`

  useEffect(() => {
    const player = audioRef.current
    if (!player) return undefined
    setAudioNotice('')
    player.currentTime = 0
    player.play().catch(() => {
      setAudioNotice('La lecture automatique a été bloquée. Appuyez sur « Réécouter » pour entendre la question.')
    })
    return () => player.pause()
  }, [question.audio_url])

  async function submitAnswer(blob) {
    setBusy(true)
    setError('')
    try {
      setResult(await envoyerReponse(sessionId, blob))
    } catch (cause) {
      setError(cause.message)
    } finally {
      setBusy(false)
    }
  }

  function replayQuestion() {
    if (!audioRef.current) return
    audioRef.current.currentTime = 0
    audioRef.current.play().catch(() => {
      setAudioNotice('La lecture audio ne démarre pas. Vérifiez le volume de votre appareil.')
    })
  }

  return (
    <main className="page-shell">
      <header className="brand-row">
        <a className="wordmark" href="/" aria-label="Mahara accueil">mahara<span>.</span></a>
        <span className="brand-caption">Espace candidat</span>
      </header>
      <section className="flow-content" aria-labelledby="question-title">
        <div className="progress-heading">
          <span>VOTRE PARCOURS</span>
          <span>Question {questionNumber} sur {QUESTION_ORDER.length}</span>
        </div>
        <div
          className="progress-track"
          role="progressbar"
          aria-label={`Question ${questionNumber} sur ${QUESTION_ORDER.length}`}
          aria-valuemin="1"
          aria-valuemax={QUESTION_ORDER.length}
          aria-valuenow={questionNumber}
        >
          <span style={{ width: progress }} />
        </div>

        <p className="eyebrow">QUESTION {String(questionNumber).padStart(2, '0')}</p>
        <h1 id="question-title" dir="auto">{question.texte}</h1>
        <audio ref={audioRef} src={question.audio_url} preload="auto" />
        <button className="replay-button" type="button" onClick={replayQuestion} disabled={busy || Boolean(result)}>
          <span aria-hidden="true">↻</span> Réécouter la question
        </button>
        {audioNotice && <p className="message message-subtle" role="status">{audioNotice}</p>}

        {!result ? (
          <div className="answer-panel">
            <RecorderControls
              onRecorded={submitAnswer}
              disabled={busy}
              retryAvailable={Boolean(error)}
              onRetry={() => setError('')}
            />
            {busy && (
              <p className="transcription-status" role="status">
                <span className="status-spinner" aria-hidden="true" /> Transcription en cours
              </p>
            )}
            {error && <p className="message message-error" role="alert">{error}</p>}
          </div>
        ) : (
          <section className="result-panel" aria-labelledby="result-title">
            <p className="result-kicker" id="result-title">Réponse enregistrée</p>
            <dl className="recognized-values">
              <div>
                <dt>Ce que vous avez dit</dt>
                <dd dir="auto">{result.texte_brut}</dd>
              </div>
              <div>
                <dt>Valeur retenue</dt>
                <dd dir="auto">{result.valeur_extraite ?? 'Non extraite'}</dd>
              </div>
            </dl>
            <button
              className="button button-primary button-large"
              type="button"
              onClick={() => result.termine ? onFinish() : onNext(result.question_suivante)}
            >
              {result.termine ? 'Voir mon offre' : 'Suivant'}
              <span className="button-arrow" aria-hidden="true">→</span>
            </button>
          </section>
        )}
      </section>
      <footer className="page-footer"><span>Mahara Match</span><span>Question {questionNumber} / 4</span></footer>
    </main>
  )
}