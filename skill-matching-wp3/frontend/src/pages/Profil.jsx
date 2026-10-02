import { useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { parseCv } from '../api.js'
import ErrorMessage from '../components/ErrorMessage.jsx'
import Spinner from '../components/Spinner.jsx'
import { useCandidat } from '../context/CandidatContext.jsx'
import { gouvernorats, nomGouvernorat } from '../governorates.js'

function Profil() {
  const { candidatId, setCandidatId, profil, setProfil } = useCandidat()
  const [governorateCode, setGovernorateCode] = useState('')
  const [file, setFile] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [dragging, setDragging] = useState(false)
  const inputRef = useRef(null)
  const navigate = useNavigate()

  function chooseFile(nextFile) {
    if (!nextFile) return
    if (!/\.(pdf|docx)$/i.test(nextFile.name)) {
      setError('Format non valide. Choisissez un fichier PDF ou DOCX.')
      setFile(null)
      return
    }
    setError('')
    setFile(nextFile)
  }

  async function submit(event) {
    event.preventDefault()
    if (!candidatId.trim()) return setError('Saisissez un identifiant candidat.')
    if (!file) return setError('Sélectionnez votre CV au format PDF ou DOCX.')
    setLoading(true)
    setError('')
    try {
      const result = await parseCv(candidatId.trim(), governorateCode, file)
      setProfil(result.profil)
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setLoading(false)
    }
  }

  const skills = profil?.skills || []

  return (
    <div className="page">
      <header className="page-heading">
        <div><p className="eyebrow">VOTRE PARCOURS</p><h1>Mon profil</h1><p className="page-intro">Votre expérience et vos compétences, extraites de votre CV.</p></div>
        <span className="heading-mark">01 <i>/ 04</i></span>
      </header>

      <form className="panel upload-panel" onSubmit={submit}>
        <div className="panel-heading"><div><span className="step-label">ÉTAPE 01</span><h2>Importer mon CV</h2></div><span className="panel-icon">CV</span></div>
        <div className="form-grid">
          <label className="field"><span>Identifiant candidat</span><input value={candidatId} onChange={(event) => setCandidatId(event.target.value)} placeholder="demo" /></label>
          <label className="field"><span>Gouvernorat</span><select value={governorateCode} onChange={(event) => setGovernorateCode(event.target.value)}><option value="">Sélectionner un gouvernorat</option>{gouvernorats.map(([code, name]) => <option key={code} value={code}>{name}</option>)}</select></label>
        </div>
        <div className={`drop-zone${dragging ? ' dragging' : ''}`} onDragOver={(event) => { event.preventDefault(); setDragging(true) }} onDragLeave={() => setDragging(false)} onDrop={(event) => { event.preventDefault(); setDragging(false); chooseFile(event.dataTransfer.files[0]) }}>
          <span className="upload-icon" aria-hidden="true">↑</span>
          <strong>{file ? file.name : 'Déposez votre CV ici'}</strong>
          <span>{file ? 'Fichier prêt à être analysé' : 'PDF ou DOCX · formats acceptés uniquement'}</span>
          <input ref={inputRef} type="file" accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document" hidden onChange={(event) => chooseFile(event.target.files[0])} />
          <button className="button button-secondary" type="button" onClick={() => inputRef.current?.click()}>Choisir un fichier</button>
        </div>
        {error && <ErrorMessage message={error} />}
        <div className="form-footer"><span className="privacy-note">Aucune donnée personnelle n’est affichée.</span><button className="button button-primary" type="submit" disabled={loading}>{loading ? 'Analyse en cours…' : 'Téléverser mon CV'}<span aria-hidden="true">↗</span></button></div>
      </form>

      {loading && <Spinner label="Analyse du CV en cours…" />}

      {profil && !loading && <section className="panel profile-result">
        <div className="panel-heading"><div><span className="step-label">PROFIL ANALYSÉ</span><h2>Votre aperçu</h2></div><span className="success-label"><i />Analyse terminée</span></div>
        <div className="profile-facts">
          <div><small>Expérience</small><strong>{profil.years_experience} <span>ans</span></strong></div>
          <div><small>Gouvernorat</small><strong>{nomGouvernorat(profil.location?.governorate_code)}</strong></div>
          <div><small>Mobilité</small><strong>{profil.mobility?.radius_km || 0} <span>km</span></strong></div>
        </div>
        <div className="skill-groups">
          <div className="skill-group"><h3>Compétences techniques</h3><div className="chips">{skills.filter((skill) => skill.skill_type === 'hard').map((skill, index) => <span className="skill-chip" key={`${skill.label_raw}-${index}`}>{skill.label_raw} · niveau {skill.level}</span>)}{!skills.some((skill) => skill.skill_type === 'hard') && <span className="muted">Aucune compétence détectée</span>}</div></div>
          <div className="skill-group"><h3>Compétences relationnelles</h3><div className="chips">{skills.filter((skill) => skill.skill_type === 'soft').map((skill, index) => <span className="skill-chip soft" key={`${skill.label_raw}-${index}`}>{skill.label_raw} · niveau {skill.level}</span>)}{!skills.some((skill) => skill.skill_type === 'soft') && <span className="muted">Aucune compétence détectée</span>}</div></div>
        </div>
        <div className="summary-block"><h3>Résumé</h3><p>{profil.summary || 'Aucun résumé n’a été extrait du CV.'}</p></div>
        <button className="button button-primary" onClick={() => navigate('/offres')}>Voir mes offres recommandées <span aria-hidden="true">→</span></button>
      </section>}
    </div>
  )
}

export default Profil