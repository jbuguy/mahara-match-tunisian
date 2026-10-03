import textes from '../textes.js'

export default function WelcomeScreen({ onStart, loading, error }) {
  return (
    <main className="page-shell">
      <header className="brand-row">
        <a className="wordmark" href="/" aria-label={textes.espaceCandidat}>{textes.marque}<span>.</span></a>
        <span className="brand-caption">{textes.espaceCandidat}</span>
      </header>
      <section className="welcome-content" aria-labelledby="welcome-title">
        <div className="welcome-mark" aria-hidden="true">
          <span className="mark-line mark-line-one" />
          <span className="mark-line mark-line-two" />
          <span className="mark-dot" />
        </div>
        <p className="eyebrow">{textes.nombreQuestions}</p>
        <h1 id="welcome-title">{textes.accueilTitre}</h1>
        <p className="welcome-copy">{textes.accueilDescription}</p>
        <button className="button button-primary button-large" type="button" onClick={onStart} disabled={loading}>
          {loading ? textes.preparation : textes.commencer}
          <span className="button-arrow" aria-hidden="true">←</span>
        </button>
        {error && <p className="message message-error" role="alert">{error}</p>}
        <p className="privacy-note">{textes.confidentialite}</p>
      </section>
      <footer className="page-footer"><span>{textes.marque}</span><span>{textes.aTonRythme}</span></footer>
    </main>
  )
}