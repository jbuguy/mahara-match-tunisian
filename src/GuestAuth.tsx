import { useState, type FormEvent } from "react";
import { ArrowLeft } from "lucide-react";
import { demoAccounts } from "./auth";

export function GuestAuth({
  error,
  isRegistering,
  pendingNote,
  onModeChange,
  onAuthenticate,
}: {
  error: string;
  isRegistering: boolean;
  pendingNote: string;
  onModeChange: (registering: boolean) => void;
  onAuthenticate: (
    event: FormEvent<HTMLFormElement>,
    email: string,
    password: string,
    isRegistration: boolean,
  ) => Promise<void>;
}) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  return (
    <main className="guest-auth">
      <section className="guest-auth__brand-panel">
        <a className="guest-brand" href="#accueil" aria-label="Retour à Mahara Match">
          <span className="guest-brand__mark" aria-hidden="true">m</span>
          <span>mahara<span>match</span></span>
        </a>
        <div className="guest-auth__brand-copy">
          <p className="guest-eyebrow">LE TALENT TROUVE SA PLACE</p>
          <h1>Votre prochaine étape commence ici.</h1>
          <p>Connectez vos compétences aux opportunités qui vous ressemblent.</p>
        </div>
        <a className="guest-auth__back" href="#accueil">
          <ArrowLeft size={17} aria-hidden="true" />
          Retour à la découverte
        </a>
      </section>

      <section className="guest-auth__form-panel" aria-labelledby="guest-auth-title">
        <div className="guest-auth__form-wrap">
          <div className="guest-auth__tabs" role="tablist" aria-label="Accès à votre compte">
            <button
              type="button"
              role="tab"
              id="guest-auth-tab-login"
              aria-selected={!isRegistering}
              aria-controls="guest-auth-panel"
              onClick={() => onModeChange(false)}
            >
              Se connecter
            </button>
            <button
              type="button"
              role="tab"
              id="guest-auth-tab-register"
              aria-selected={isRegistering}
              aria-controls="guest-auth-panel"
              onClick={() => onModeChange(true)}
            >
              Créer un compte
            </button>
          </div>
          <div id="guest-auth-panel" role="tabpanel" aria-labelledby={isRegistering ? "guest-auth-tab-register" : "guest-auth-tab-login"}>
            <p className="guest-eyebrow">BIENVENUE SUR MAHARA MATCH</p>
            <h2 id="guest-auth-title">
              {isRegistering ? "Créez votre espace candidat" : "Ravi·e de vous revoir"}
            </h2>
            <p className="guest-auth__intro">
              {isRegistering
                ? "Créez votre compte, puis complétez votre profil avec l’assistant."
                : "Connectez-vous pour retrouver vos opportunités et poursuivre votre parcours."}
            </p>
            {pendingNote && <p className="guest-auth__pending">{pendingNote}</p>}
            <form
              className="guest-auth__form"
              onSubmit={(event) => void onAuthenticate(event, email, password, isRegistering)}
            >
              <label>
                <span>Adresse e-mail</span>
                <input
                  autoComplete={isRegistering ? "email" : "username"}
                  type="email"
                  required
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                />
              </label>
              <label>
                <span>Mot de passe</span>
                <input
                  autoComplete={isRegistering ? "new-password" : "current-password"}
                  type="password"
                  required
                  minLength={isRegistering ? 12 : undefined}
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                />
              </label>
              {isRegistering && <p className="guest-auth__hint">Utilisez au moins 12 caractères.</p>}
              {error && <p className="guest-error" role="alert">{error}</p>}
              <button type="submit" className="guest-button guest-button--terracotta guest-auth__submit">
                {isRegistering ? "Créer mon compte" : "Se connecter"}
              </button>
            </form>
            {!isRegistering && (
              <div className="guest-auth__demo">
                <strong>Comptes de démonstration</strong>
                <p>Choisissez un compte pour remplir son adresse e-mail. Le mot de passe est fourni lors du seed local.</p>
                <div>
                  {demoAccounts.map((account) => (
                    <button key={account.role} type="button" onClick={() => setEmail(account.email)}>
                      {account.label}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </section>
    </main>
  );
}
