import { Link } from 'react-router-dom'
import { useI18n } from '../lib/i18n'

const setupOptions = [
  { number: '01', icon: '♬', titleKey: 'candidate.voiceTitle', label: 'VOCAL INTELLIGENT', descriptionKey: 'candidate.voiceDescription', actionKey: 'candidate.startVoice', href: '/onboarding', featured: true },
  { number: '02', icon: '✦', titleKey: 'candidate.assistantTitle', label: 'GUIDAGE CONVERSATIONNEL', descriptionKey: 'candidate.assistantDescription', actionKey: 'candidate.openAssistant', href: '/candidate#assistant', featured: false },
  { number: '03', icon: '▣', titleKey: 'candidate.cvTitle', label: 'EXTRACTION SÉCURISÉE', descriptionKey: 'candidate.cvDescription', actionKey: 'candidate.importCv', href: '/candidate#cv-import', featured: false },
] as const

export function CandidateStartPage() {
  const { language, setLanguage, t } = useI18n()
  return <div className="candidate-start-screen">
    <header className="candidate-start-topbar"><Link to="/dashboard" className="candidate-start-brand"><span>▣</span><strong>Mahara Match</strong><small>مهارة ماتش</small></Link><div className="candidate-start-status">● {language === 'en' ? 'Candidate' : language === 'ar' ? 'مترشح' : 'Candidat'} — <b>{language === 'en' ? 'New profile' : language === 'ar' ? 'ملف جديد' : 'Nouveau profil'}</b></div><div className="candidate-start-languages"><button type="button" className={language === 'fr' ? 'active' : ''} onClick={() => setLanguage('fr')}>FR</button><button type="button" className={language === 'en' ? 'active' : ''} onClick={() => setLanguage('en')}>EN</button><button type="button" className={language === 'ar' ? 'active' : ''} onClick={() => setLanguage('ar')}>العربية</button></div></header>
    <div className="candidate-start-crumb"><Link to="/dashboard">Accueil</Link><span>/</span><span>Espace candidat</span><span>/</span><b>Création du profil guidée</b></div>
    <section className="candidate-start-heading"><span>ÉTAPE 1 · MÉTHODE D’INITIATION</span><h1>{t('candidate.setupTitle')}</h1><p>{t('candidate.setupDescription')}</p></section>
    <section className="candidate-start-options-new" aria-label="Méthodes de création du profil">{setupOptions.map((option) => <article key={option.number} className={option.featured ? 'featured' : ''}><div className="candidate-option-top"><span>{option.number}</span>{option.featured && <b>Le plus rapide · 3 min chrono</b>}</div><div className="candidate-option-icon">{option.icon}</div><small>{option.label}</small><h2>{t(option.titleKey)}</h2><p>{t(option.descriptionKey)}</p><Link to={option.href}>{t(option.actionKey)}<span>→</span></Link></article>)}</section>
    <div className="candidate-start-note"><span>▣</span><p><strong>{t('candidate.dataControl')}</strong> {language === 'en' ? 'You can review, correct, or delete every detail before finalizing your profile.' : language === 'ar' ? 'يمكنك مراجعة كل معلومة وتصحيحها أو حذفها قبل إتمام ملفك.' : 'Vous pourrez revoir, corriger ou supprimer chaque information avant de finaliser votre profil.'}</p><Link to="/signup">{language === 'en' ? 'Back to sign up' : language === 'ar' ? 'العودة إلى التسجيل' : 'Retour à l’inscription'}</Link></div>
  </div>
}
