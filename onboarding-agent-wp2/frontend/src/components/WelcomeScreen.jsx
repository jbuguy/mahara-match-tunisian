export default function WelcomeScreen({ onStart, loading, error }) {
  return (
    <main className="page-shell">
      <header className="brand-row">
        <a className="wordmark" href="/" aria-label="Mahara accueil">mahara<span>.</span></a>
        <span className="brand-caption">Espace candidat</span>
      </header>
      <section className="welcome-content" aria-labelledby="welcome-title">
        <div className="welcome-mark" aria-hidden="true">
          <span className="mark-line mark-line-one" />
          <span className="mark-line mark-line-two" />
          <span className="mark-dot" />
        </div>
        <p className="eyebrow">Parcours vocal · 4 questions</p>
        <h1 id="welcome-title">Parlons de votre prochain travail.</h1>
        <p className="welcome-copy">
          Répondez simplement à quelques questions vocales. Votre offre sera préparée à la fin.
        </p>
        <button className="button button-primary button-large" type="button" onClick={onStart} disabled={loading}>
          {loading ? 'Préparation…' : 'Commencer'}
          <span className="button-arrow" aria-hidden="true">→</span>
        </button>
        {error && <p className="message message-error" role="alert">{error}</p>}
        <p className="privacy-note">Vos réponses sont recueillies uniquement pour préparer votre offre.</p>
      </section>
      <footer className="page-footer"><span>Mahara Match</span><span>Votre parcours, à votre rythme</span></footer>
    </main>
  )
}