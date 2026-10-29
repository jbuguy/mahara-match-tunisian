import { Link } from 'react-router-dom'

export function PublicOnboardingPage() {
  return <div className="public-onboarding">
    <div className="public-onboarding-crumb">MAHARA MATCH · PLATEFORME PUBLIQUE DE L’EMPLOI</div>
    <section className="public-onboarding-hero">
      <div className="public-onboarding-copy"><span className="public-onboarding-badge">✦ ATELIER NUMÉRIQUE DE LA MÉDINA</span><h1>Votre prochaine étape commence ici.</h1><p>Mahara Match relie les talents, les entreprises et les centres de formation tunisiens autour de compétences reconnues et d’opportunités concrètes.</p><div className="public-onboarding-actions"><Link className="public-onboarding-primary" to="/signup">Créer mon compte →</Link><Link className="public-onboarding-secondary" to="/signin">Se connecter</Link></div></div>
      <div className="public-onboarding-mark" aria-hidden="true"><span>مهارة</span><strong>M</strong><span>ماتش</span></div>
    </section>
    <section className="public-onboarding-grid" aria-label="Mahara Match services"><article><span>01</span><h2>Construisez votre profil</h2><p>Présentez vos savoir-faire, votre expérience et vos aspirations dans un profil clair.</p><Link to="/signup?role=candidate">Je cherche un emploi ↗</Link></article><article><span>02</span><h2>Trouvez les bonnes opportunités</h2><p>Découvrez des offres adaptées à vos compétences et préparez vos prochaines étapes.</p><Link to="/signup?role=candidate">Explorer mon parcours ↗</Link></article><article><span>03</span><h2>Recrutez avec confiance</h2><p>Publiez des offres utiles et rencontrez des talents vérifiés partout en Tunisie.</p><Link to="/signup?role=employer">Je recrute des talents ↗</Link></article></section>
    <footer className="public-onboarding-footer"><span>Une passerelle souveraine pour les compétences tunisiennes.</span><span>Français　·　العربية　·　Tounsi</span></footer>
  </div>
}
