import { useState, type FormEvent } from 'react';
import { ArrowRight, BriefcaseBusiness, LockKeyhole, Mail, Sparkles } from 'lucide-react';

interface AuthScreenProps {
  onAuthenticated: (token: string) => void;
}

type AuthMode = 'login' | 'signup';

export function AuthScreen({ onAuthenticated }: AuthScreenProps) {
  const [mode, setMode] = useState<AuthMode>('login');
  const [pending, setPending] = useState(false);
  const [error, setError] = useState('');

  async function signIn(email: string, password: string) {
    const response = await fetch('/employers/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(typeof body.detail === 'string' ? body.detail : 'Vérifiez votre adresse et votre mot de passe.');
    onAuthenticated(body.access_token as string);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = Object.fromEntries(new FormData(form));
    setPending(true);
    setError('');
    try {
      if (mode === 'signup') {
        const response = await fetch('/employers/signup', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(data),
        });
        const body = await response.json().catch(() => ({}));
        if (!response.ok) {
          const validation = Array.isArray(body.detail)
            ? body.detail.map((item: { msg?: string }) => item.msg).filter(Boolean).join(' · ')
            : '';
          throw new Error(response.status === 409 ? 'Cette adresse e-mail est déjà utilisée.' : validation || 'Vérifiez les informations de votre entreprise.');
        }
        await signIn(String(data.email), String(data.password));
      } else {
        await signIn(String(data.email), String(data.password));
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Inscription impossible. Réessayez.');
    } finally {
      setPending(false);
    }
  }

  return (
    <main className="auth-shell">
      <section className="auth-story" aria-label="Mahara Match">
        <div className="brand-lockup"><span className="brand-mark"><BriefcaseBusiness size={19} /></span><span>MAHARA MATCH <small>ESPACE RECRUTEUR</small></span></div>
        <div className="story-copy">
          <span className="eyebrow"><Sparkles size={14} /> Rédaction d'offre assistée</span>
          <h1>Le bon poste commence par une offre claire.</h1>
          <p>Structurez votre besoin, choisissez votre rythme et relisez une offre pensée pour les personnes qui la découvriront.</p>
        </div>
        <div className="story-footer"><span>FRANÇAIS · DERJA</span><span>RECRUTER AVEC INTENTION</span></div>
      </section>
      <section className="auth-panel" aria-labelledby="auth-title">
        <div className="auth-topline"><span>Mahara Match</span><span>01 <i>/</i> 02</span></div>
        <div className="auth-form-wrap">
          <p className="eyebrow">{mode === 'login' ? 'Bienvenue' : 'Nouvel espace recruteur'}</p>
          <h2 id="auth-title">{mode === 'login' ? 'Connectez-vous' : 'Créez votre compte'}</h2>
          <p className="auth-intro">{mode === 'login' ? 'Retrouvez vos offres en cours et continuez là où vous en étiez.' : 'Quelques informations pour configurer votre espace.'}</p>
          <div className="auth-tabs" role="tablist" aria-label="Accès au compte">
            <button type="button" role="tab" aria-selected={mode === 'login'} className={mode === 'login' ? 'active' : ''} onClick={() => { setMode('login'); setError(''); }}>Connexion</button>
            <button type="button" role="tab" aria-selected={mode === 'signup'} className={mode === 'signup' ? 'active' : ''} onClick={() => { setMode('signup'); setError(''); }}>Créer un compte</button>
          </div>
          <form className="auth-form" onSubmit={handleSubmit}>
            {mode === 'signup' && <>
              <label>Entreprise<input name="company_name" autoComplete="organization" placeholder="Ex. Atelier Sirocco" required /></label>
              <div className="form-row">
                <label>Secteur<input name="sector" placeholder="Ex. Services numériques" required /></label>
                <label>Effectif<select name="company_size" defaultValue="" required><option value="" disabled>Choisir</option><option value="1-10">1–10</option><option value="11-50">11–50</option><option value="51-200">51–200</option><option value="200+">200+</option></select></label>
              </div>
            </>}
            <label>Adresse e-mail<span className="input-icon"><Mail size={16} /><input name="email" type="email" autoComplete="email" placeholder="vous@entreprise.tn" required /></span></label>
            <label>Mot de passe<span className="input-icon"><LockKeyhole size={16} /><input name="password" type="password" autoComplete={mode === 'login' ? 'current-password' : 'new-password'} placeholder={mode === 'login' ? 'Votre mot de passe' : '8 caractères, avec majuscule et chiffre'} minLength={8} maxLength={128} pattern={mode === 'signup' ? '(?=.*[a-z])(?=.*[A-Z])(?=.*[0-9]).{8,128}' : undefined} title="Utilisez 8 à 128 caractères avec une majuscule, une minuscule et un chiffre." required /></span></label>
            {error && <p className="form-error" role="alert">{error}</p>}
            <button className="button-primary auth-submit" disabled={pending} type="submit">{pending ? 'Un instant…' : mode === 'login' ? 'Entrer dans mon espace' : 'Créer mon espace'}<ArrowRight size={17} /></button>
          </form>
          <p className="auth-note">Vos brouillons restent privés et accessibles uniquement depuis votre compte.</p>
        </div>
      </section>
    </main>
  );
}