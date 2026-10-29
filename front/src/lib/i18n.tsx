import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'

export type Language = 'fr' | 'en' | 'ar'

type TranslationKey =
  | 'brand.platform'
  | 'nav.signIn'
  | 'nav.createAccount'
  | 'nav.overview'
  | 'nav.profile'
  | 'nav.matches'
  | 'nav.interview'
  | 'nav.setupProfile'
  | 'nav.searchPlaceholder'
  | 'nav.changeLanguage'
  | 'nav.notifications'
  | 'nav.activeWorkspace'
  | 'nav.loadingWorkspace'
  | 'status.loading'
  | 'status.ok'
  | 'auth.forgotPassword'
  | 'auth.signIn'
  | 'auth.signUp'
  | 'auth.backToSignIn'
  | 'auth.email'
  | 'auth.password'
  | 'auth.sendResetLink'
  | 'auth.resetPassword'
  | 'auth.passwordResetTitle'
  | 'auth.passwordForgotTitle'
  | 'auth.passwordResetDescription'
  | 'auth.passwordForgotDescription'
  | 'candidate.setupTitle'
  | 'candidate.setupDescription'
  | 'candidate.voiceTitle'
  | 'candidate.voiceDescription'
  | 'candidate.assistantTitle'
  | 'candidate.assistantDescription'
  | 'candidate.cvTitle'
  | 'candidate.cvDescription'
  | 'candidate.startVoice'
  | 'candidate.openAssistant'
  | 'candidate.importCv'
  | 'candidate.dataControl'
  | 'matches.title'
  | 'matches.signInDescription'
  | 'matches.noOffersTitle'
  | 'matches.noOffersDescription'
  | 'common.tryAgain'

const translations: Record<Language, Record<TranslationKey, string>> = {
  fr: {
    'brand.platform': 'Plateforme nationale de l’emploi et des compétences', 'nav.signIn': 'Se connecter', 'nav.createAccount': 'Créer un compte', 'nav.overview': 'Vue d’ensemble', 'nav.profile': 'Mon profil', 'nav.matches': 'Mes opportunités', 'nav.interview': 'Préparer un entretien', 'nav.setupProfile': 'Créer mon profil', 'nav.searchPlaceholder': 'Rechercher une compétence, une offre ou un métier…', 'nav.changeLanguage': 'Changer de langue', 'nav.notifications': 'Notifications', 'nav.activeWorkspace': 'Espace actif', 'nav.loadingWorkspace': 'Chargement de votre espace…', 'status.loading': 'Chargement…', 'status.ok': 'Opérationnel', 'auth.forgotPassword': 'Mot de passe oublié ?', 'auth.signIn': 'Se connecter', 'auth.signUp': 'Créer un compte', 'auth.backToSignIn': 'Retour à la connexion', 'auth.email': 'Adresse e-mail', 'auth.password': 'Mot de passe', 'auth.sendResetLink': 'Envoyer le lien', 'auth.resetPassword': 'Réinitialiser le mot de passe', 'auth.passwordResetTitle': 'Choisir un nouveau mot de passe', 'auth.passwordForgotTitle': 'Mot de passe oublié ?', 'auth.passwordResetDescription': 'Utilisez au moins 8 caractères avec une majuscule, une minuscule et un chiffre.', 'auth.passwordForgotDescription': 'Saisissez votre adresse e-mail et nous vous enverrons un lien sécurisé.', 'candidate.setupTitle': 'Choisissez votre mode de création de profil', 'candidate.setupDescription': 'Choisissez la manière qui vous convient : parlez, échangez avec l’assistant ou importez votre CV.', 'candidate.voiceTitle': 'Parlez avec nous', 'candidate.voiceDescription': 'Répondez en français ou en derja tunisienne. Votre voix est transformée en profil structuré.', 'candidate.assistantTitle': 'Discutez avec l’assistant', 'candidate.assistantDescription': 'Décrivez votre expérience à votre rythme, puis vérifiez chaque information.', 'candidate.cvTitle': 'Importez votre CV', 'candidate.cvDescription': 'Importez un PDF ou un document Word et vérifiez les informations extraites.', 'candidate.startVoice': 'Démarrer l’atelier vocal', 'candidate.openAssistant': 'Ouvrir l’assistant profil', 'candidate.importCv': 'Choisir un CV', 'candidate.dataControl': 'Vos données restent sous votre contrôle.', 'matches.title': 'Mes opportunités', 'matches.signInDescription': 'Connectez-vous pour voir les offres correspondant à votre profil.', 'matches.noOffersTitle': 'Aucune offre à afficher pour le moment', 'matches.noOffersDescription': 'Les nouvelles opportunités apparaîtront ici.', 'common.tryAgain': 'Réessayer',
  },
  en: {
    'brand.platform': 'National employment and skills platform', 'nav.signIn': 'Sign in', 'nav.createAccount': 'Create account', 'nav.overview': 'Overview', 'nav.profile': 'My profile', 'nav.matches': 'Job matches', 'nav.interview': 'Interview practice', 'nav.setupProfile': 'Set up my profile', 'nav.searchPlaceholder': 'Search for a skill, job offer, or occupation…', 'nav.changeLanguage': 'Change language', 'nav.notifications': 'Notifications', 'nav.activeWorkspace': 'Active workspace', 'nav.loadingWorkspace': 'Loading your workspace…', 'status.loading': 'Loading…', 'status.ok': 'All systems operational', 'auth.forgotPassword': 'Forgot your password?', 'auth.signIn': 'Sign in', 'auth.signUp': 'Create account', 'auth.backToSignIn': 'Back to sign in', 'auth.email': 'Email address', 'auth.password': 'Password', 'auth.sendResetLink': 'Send reset link', 'auth.resetPassword': 'Reset password', 'auth.passwordResetTitle': 'Choose a new password', 'auth.passwordForgotTitle': 'Forgot your password?', 'auth.passwordResetDescription': 'Use at least 8 characters with an uppercase letter, lowercase letter, and number.', 'auth.passwordForgotDescription': 'Enter your email address and we’ll send you a secure link.', 'candidate.setupTitle': 'Choose how to create your profile', 'candidate.setupDescription': 'Choose what works for you: speak, chat with the assistant, or import your CV.', 'candidate.voiceTitle': 'Speak with us', 'candidate.voiceDescription': 'Answer in French or Tunisian Derja. Your voice becomes a structured profile.', 'candidate.assistantTitle': 'Talk with the assistant', 'candidate.assistantDescription': 'Describe your experience at your own pace, then review every detail.', 'candidate.cvTitle': 'Import your CV', 'candidate.cvDescription': 'Upload a PDF or Word document and review the extracted information.', 'candidate.startVoice': 'Start voice workshop', 'candidate.openAssistant': 'Open profile assistant', 'candidate.importCv': 'Choose a CV', 'candidate.dataControl': 'Your data stays under your control.', 'matches.title': 'Your job matches', 'matches.signInDescription': 'Sign in to see roles matched to your candidate profile.', 'matches.noOffersTitle': 'No offers to match yet', 'matches.noOffersDescription': 'New opportunities will appear here when they are available.', 'common.tryAgain': 'Try again',
  },
  ar: {
    'brand.platform': 'المنصة الوطنية للتشغيل والمهارات', 'nav.signIn': 'تسجيل الدخول', 'nav.createAccount': 'إنشاء حساب', 'nav.overview': 'نظرة عامة', 'nav.profile': 'ملفي الشخصي', 'nav.matches': 'الفرص المناسبة', 'nav.interview': 'التدرّب على المقابلة', 'nav.setupProfile': 'إنشاء ملفي الشخصي', 'nav.searchPlaceholder': 'ابحث عن مهارة أو عرض عمل أو مهنة…', 'nav.changeLanguage': 'تغيير اللغة', 'nav.notifications': 'الإشعارات', 'nav.activeWorkspace': 'المساحة النشطة', 'nav.loadingWorkspace': 'جارٍ تحميل مساحتك…', 'status.loading': 'جارٍ التحميل…', 'status.ok': 'الخدمة تعمل', 'auth.forgotPassword': 'نسيت كلمة المرور؟', 'auth.signIn': 'تسجيل الدخول', 'auth.signUp': 'إنشاء حساب', 'auth.backToSignIn': 'العودة إلى تسجيل الدخول', 'auth.email': 'البريد الإلكتروني', 'auth.password': 'كلمة المرور', 'auth.sendResetLink': 'إرسال الرابط', 'auth.resetPassword': 'إعادة تعيين كلمة المرور', 'auth.passwordResetTitle': 'اختيار كلمة مرور جديدة', 'auth.passwordForgotTitle': 'نسيت كلمة المرور؟', 'auth.passwordResetDescription': 'استعمل 8 أحرف على الأقل، مع حرف كبير وحرف صغير ورقم.', 'auth.passwordForgotDescription': 'أدخل بريدك الإلكتروني وسنرسل لك رابطاً آمناً.', 'candidate.setupTitle': 'اختر طريقة إنشاء ملفك الشخصي', 'candidate.setupDescription': 'اختر ما يناسبك: تحدث، أو استعمل المساعد، أو استورد سيرتك الذاتية.', 'candidate.voiceTitle': 'تحدث معنا', 'candidate.voiceDescription': 'أجب بالفرنسية أو الدارجة التونسية وسنحوّل صوتك إلى ملف منظم.', 'candidate.assistantTitle': 'تحدث مع المساعد', 'candidate.assistantDescription': 'صف تجربتك على راحتك، ثم راجع كل معلومة قبل حفظها.', 'candidate.cvTitle': 'استورد سيرتك الذاتية', 'candidate.cvDescription': 'ارفع ملف PDF أو Word وراجع المعلومات المستخرجة.', 'candidate.startVoice': 'ابدأ الورشة الصوتية', 'candidate.openAssistant': 'افتح مساعد الملف الشخصي', 'candidate.importCv': 'اختر سيرة ذاتية', 'candidate.dataControl': 'بياناتك تبقى تحت سيطرتك.', 'matches.title': 'الفرص المناسبة لك', 'matches.signInDescription': 'سجّل الدخول لرؤية الوظائف المناسبة لملفك.', 'matches.noOffersTitle': 'لا توجد عروض مناسبة بعد', 'matches.noOffersDescription': 'ستظهر الفرص الجديدة هنا عند توفرها.', 'common.tryAgain': 'حاول مرة أخرى',
  },
}

type I18nContextValue = { language: Language; setLanguage: (language: Language) => void; t: (key: TranslationKey) => string; direction: 'ltr' | 'rtl' }
const I18nContext = createContext<I18nContextValue | null>(null)

export function I18nProvider({ children }: { children: ReactNode }) {
  const [language, setLanguageState] = useState<Language>(() => (localStorage.getItem('mahara_language') as Language | null) ?? 'fr')
  const direction: 'ltr' | 'rtl' = language === 'ar' ? 'rtl' : 'ltr'

  useEffect(() => {
    localStorage.setItem('mahara_language', language)
    document.documentElement.lang = language
    document.documentElement.dir = direction
  }, [direction, language])

  const value = useMemo(() => ({ language, direction, setLanguage: setLanguageState, t: (key: TranslationKey) => translations[language][key] }), [direction, language])
  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>
}

export function useI18n() {
  const context = useContext(I18nContext)
  if (!context) throw new Error('useI18n must be used inside I18nProvider')
  return context
}
