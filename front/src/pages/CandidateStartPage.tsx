import { Link } from 'react-router-dom'

export function CandidateStartPage() {
  return (
    <div className="stacked-view candidate-start">
      <header className="panel-header">
        <div>
          <p className="eyebrow">Candidate workspace</p>
          <h2>How would you like to start?</h2>
          <p>Choose a way to build your profile. You can review every detail before saving.</p>
        </div>
      </header>
      <section className="candidate-start-options" aria-label="Profile setup options">
        <article className="candidate-start-option">
          <span className="start-number">01</span>
          <h3>Speak your answers</h3>
          <p>Answer four short questions by voice, then check the details together.</p>
          <Link className="primary-btn" to="/onboarding">Start voice intake</Link>
        </article>
        <article className="candidate-start-option">
          <span className="start-number">02</span>
          <h3>Build it with an assistant</h3>
          <p>Describe your experience in French, Arabic, or Derja. Speak or type.</p>
          <Link className="secondary-btn" to="/candidate#assistant">Open profile assistant</Link>
        </article>
        <article className="candidate-start-option">
          <span className="start-number">03</span>
          <h3>Import your CV</h3>
          <p>Start with a PDF or Word CV, then review the information found.</p>
          <Link className="secondary-btn" to="/candidate#cv-import">Choose a CV</Link>
        </article>
      </section>
    </div>
  )
}