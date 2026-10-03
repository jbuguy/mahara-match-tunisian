import { useEffect, useRef, useState } from 'react'
import { envoyerReponse } from '../api.js'
import RecorderControls from './RecorderControls.jsx'
import textes from '../textes.js'

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
      setAudioNotice(textes.audioBloque)
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
      setAudioNotice(textes.erreurLectureAudio)
    })
  }

  return (
    <main className="page-shell">
      <header className="brand-row">
        <a className="wordmark" href="/" aria-label={textes.espaceCandidat}>{textes.marque}<span>.</span></a>
        <span className="brand-caption">{textes.espaceCandidat}</span>
      </header>
      <section className="flow-content" aria-labelledby="question-title">
        <div className="progress-heading">
          <span>{textes.parcours}</span>
          <span>{textes.questionProgression(questionNumber, QUESTION_ORDER.length)}</span>
        </div>
        <div
          className="progress-track"
          role="progressbar"
          aria-label={textes.questionProgression(questionNumber, QUESTION_ORDER.length)}
          aria-valuemin="1"
          aria-valuemax={QUESTION_ORDER.length}
          aria-valuenow={questionNumber}
        >
          <span style={{ inlineSize: progress }} />
        </div>

        <p className="eyebrow">{textes.questionNumero(questionNumber)}</p>
        <h1 id="question-title" dir="auto">{textes.questions[question.id] || textes.questionInconnue}</h1>
        <audio ref={audioRef} src={question.audio_url} preload="auto" />
        <button className="replay-button" type="button" onClick={replayQuestion} disabled={busy || Boolean(result)}>
          <span aria-hidden="true">↻</span> {textes.reecouter}
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
                <span className="status-spinner" aria-hidden="true" /> {textes.transcription}
              </p>
            )}
            {error && <p className="message message-error" role="alert">{error}</p>}
          </div>
        ) : (
          <section className="result-panel" aria-labelledby="result-title">
            <p className="result-kicker" id="result-title">{textes.reponseEnregistree}</p>
            <dl className="recognized-values">
              <div>
                <dt>{textes.ceQuiEstCompris}</dt>
                <dd dir="auto">{result.texte_brut}</dd>
              </div>
              <div>
                <dt>{textes.valeurRetenue}</dt>
                <dd dir={question.id === 'telephone' ? 'ltr' : 'auto'}>{result.valeur_extraite ?? textes.reponseNonExtraite}</dd>
              </div>
            </dl>
            <button
              className="button button-primary button-large"
              type="button"
              onClick={() => result.termine ? onFinish() : onNext(result.question_suivante)}
            >
              {result.termine ? textes.voirOffre : textes.suivant}
              <span className="button-arrow" aria-hidden="true">←</span>
            </button>
          </section>
        )}
      </section>
      <footer className="page-footer"><span>{textes.marque}</span><span>{textes.questionProgression(questionNumber, QUESTION_ORDER.length)}</span></footer>
    </main>
  )
}