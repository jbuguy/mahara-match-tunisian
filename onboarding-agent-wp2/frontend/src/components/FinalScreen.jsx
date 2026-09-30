import { useEffect, useState } from 'react'
import { getOffre, urlRecap } from '../api.js'

export default function FinalScreen({ sessionId, onRestart, restarting, restartError }) {
  const [offer, setOffer] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [decision, setDecision] = useState('')

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
        <a className="wordmark" href="/" aria-label="Mahara accueil">mahara<span>.</span></a>
        <span className="brand-caption">Espace candidat</span>
      </header>
      <section className="flow-content final-content" aria-labelledby="final-title">
        <p className="eyebrow">PARCOURS TERMINÉ</p>
        <h1 id="final-title">Votre offre est prête.</h1>
        <section className="offer-section" aria-labelledby="offer-title">
          <h2 id="offer-title">Votre proposition</h2>
          {loading ? (
            <p className="transcription-status" role="status">Préparation de votre offre…</p>
          ) : error ? (
            <p className="message message-error" role="alert">{error}</p>
          ) : (
            <div className="offer-text" dir="auto">{offer}</div>
          )}
        </section>
        <section className="recap-section" aria-labelledby="recap-title">
          <h2 id="recap-title">Récapitulatif audio</h2>
          <audio className="recap-player" controls preload="none" src={urlRecap(sessionId)}>
            Votre navigateur ne prend pas en charge la lecture audio.
          </audio>
        </section>
        <div className="decision-actions">
          <button className="button button-primary" type="button" onClick={() => setDecision('validée')} disabled={Boolean(decision)}>
            Valider
          </button>
          <button className="button button-secondary" type="button" onClick={() => setDecision('refusée')} disabled={Boolean(decision)}>
            Refuser
          </button>
        </div>
        {decision && <p className="message message-success" role="status">Votre offre est {decision} pour cette démo.</p>}
        {/* TODO: appeler le module Employeur lorsque son endpoint de publication sera disponible. */}
        <button className="text-button" type="button" onClick={onRestart} disabled={restarting}>
          {restarting ? 'Création de la session…' : 'Recommencer'}
        </button>
        {restartError && <p className="message message-error" role="alert">{restartError}</p>}
      </section>
      <footer className="page-footer"><span>Mahara Match</span><span>À bientôt</span></footer>
    </main>
  )
}