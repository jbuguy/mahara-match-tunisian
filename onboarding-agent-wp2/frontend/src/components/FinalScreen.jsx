import { useEffect, useState } from 'react'
import { getOffre, urlRecap } from '../api.js'
import textes from '../textes.js'

export default function FinalScreen({ sessionId, onRestart, restarting, restartError }) {
  const [offer, setOffer] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [decision, setDecision] = useState('')
  const offerLines = offer.split('\n')

  useEffect(() => {
    let active = true
    getOffre(sessionId)
      .then((text) => {
        if (active) setOffer(text)
      })
      .catch((cause) => {
        if (active) setError(cause.message)
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => { active = false }
  }, [sessionId])

  return (
    <main className="page-shell">
      <header className="brand-row">
        <a className="wordmark" href="/" aria-label={textes.espaceCandidat}>{textes.marque}<span>.</span></a>
        <span className="brand-caption">{textes.espaceCandidat}</span>
      </header>
      <section className="flow-content final-content" aria-labelledby="final-title">
        <p className="eyebrow">{textes.parcoursTermine}</p>
        <h1 id="final-title">{textes.offrePrete}</h1>
        <section className="offer-section" aria-labelledby="offer-title">
          <h2 id="offer-title">{textes.proposition}</h2>
          {loading ? (
            <p className="transcription-status" role="status">{textes.preparationOffre}</p>
          ) : error ? (
            <p className="message message-error" role="alert">{error}</p>
          ) : (
            <div className="offer-text" dir="rtl">
              {offerLines.map((line, index) => line.startsWith(textes.telephoneDansOffre) ? (
                <div key={index}>
                  {textes.telephoneDansOffre} <bdi dir="ltr">{line.slice(textes.telephoneDansOffre.length).trim()}</bdi>
                </div>
              ) : <div key={index}>{line}</div>)}
            </div>
          )}
        </section>
        <section className="recap-section" aria-labelledby="recap-title">
          <h2 id="recap-title">{textes.recapAudio}</h2>
          <audio className="recap-player" controls preload="none" src={urlRecap(sessionId)}>
            {textes.audioIndisponible}
          </audio>
        </section>
        <div className="decision-actions">
          <button className="button button-primary" type="button" onClick={() => setDecision('accepted')} disabled={Boolean(decision)}>
            {textes.valider}
          </button>
          <button className="button button-secondary" type="button" onClick={() => setDecision('declined')} disabled={Boolean(decision)}>
            {textes.refuser}
          </button>
        </div>
        {decision && <p className="message message-success" role="status">{decision === 'accepted' ? textes.offreValidee : textes.offreRefusee} {textes.pourLaDemo}</p>}
        {/* TODO: نشر العرض في وحدة المشغّل وقتلي يتوفّر الـ API. */}
        <button className="text-button" type="button" onClick={onRestart} disabled={restarting}>
          {restarting ? textes.creationSession : textes.recommencer}
        </button>
        {restartError && <p className="message message-error" role="alert">{restartError}</p>}
      </section>
      <footer className="page-footer"><span>{textes.marque}</span><span>{textes.aBientot}</span></footer>
    </main>
  )
}