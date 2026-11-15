import { useState, type FormEvent } from "react";
import { ArrowLeft } from "lucide-react";
import { demoAccounts } from "./auth";
import { LanguageSwitch } from "./components/LanguageSwitch";
import { translate, type Language } from "./i18n";

export function GuestAuth({
  language,
  onLanguageChange,
  error,
  isRegistering,
  pendingNote,
  onModeChange,
  onAuthenticate,
}: {
  language: Language;
  onLanguageChange: (language: Language) => void;
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
  const t = (text: string) => translate(language, text);

  return (
    <main className="guest-auth">
      <section className="guest-auth__brand-panel">
        <div className="guest-auth__brand-actions">
          <a className="guest-brand" href="#accueil" aria-label={t("Retour à Mahara Match")}>
            <span className="guest-brand__mark" aria-hidden="true">m</span>
            <span>mahara<span>match</span></span>
          </a>
          <LanguageSwitch language={language} onChange={onLanguageChange} />
        </div>
        <div className="guest-auth__brand-copy">
          <p className="guest-eyebrow">{t("LE TALENT TROUVE SA PLACE")}</p>
          <h1>{t("Votre prochaine étape commence ici.")}</h1>
          <p>{t("Connectez vos compétences aux opportunités qui vous ressemblent.")}</p>
        </div>
        <a className="guest-auth__back" href="#accueil">
          <ArrowLeft size={17} aria-hidden="true" />
          {t("Retour à la découverte")}
        </a>
      </section>

      <section className="guest-auth__form-panel" aria-labelledby="guest-auth-title">
        <div className="guest-auth__form-wrap">
          <div className="guest-auth__tabs" role="tablist" aria-label={t("Accès à votre compte")}>
            <button
              type="button"
              role="tab"
              id="guest-auth-tab-login"
              aria-selected={!isRegistering}
              aria-controls="guest-auth-panel"
              onClick={() => onModeChange(false)}
            >
              {t("Se connecter")}
            </button>
            <button
              type="button"
              role="tab"
              id="guest-auth-tab-register"
              aria-selected={isRegistering}
              aria-controls="guest-auth-panel"
              onClick={() => onModeChange(true)}
            >
              {t("Créer un compte")}
            </button>
          </div>
          <div id="guest-auth-panel" role="tabpanel" aria-labelledby={isRegistering ? "guest-auth-tab-register" : "guest-auth-tab-login"}>
            <p className="guest-eyebrow">{t("BIENVENUE SUR MAHARA MATCH")}</p>
            <h2 id="guest-auth-title">
              {t(isRegistering ? "Créez votre espace candidat" : "Ravi·e de vous revoir")}
            </h2>
            <p className="guest-auth__intro">
              {isRegistering
                ? t("Créez votre compte, puis complétez votre profil avec l’assistant.")
                : t("Connectez-vous pour retrouver vos opportunités et poursuivre votre parcours.")}
            </p>
            {pendingNote && <p className="guest-auth__pending">{pendingNote}</p>}
            <form
              className="guest-auth__form"
              onSubmit={(event) => void onAuthenticate(event, email, password, isRegistering)}
            >
              <label>
                <span>{t("Adresse e-mail")}</span>
                <input
                  autoComplete={isRegistering ? "email" : "username"}
                  type="email"
                  required
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                />
              </label>
              <label>
                <span>{t("Mot de passe")}</span>
                <input
                  autoComplete={isRegistering ? "new-password" : "current-password"}
                  type="password"
                  required
                  minLength={isRegistering ? 12 : undefined}
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                />
              </label>
              {isRegistering && <p className="guest-auth__hint">{t("Utilisez au moins 12 caractères.")}</p>}
              {error && <p className="guest-error" role="alert">{error}</p>}
              <button type="submit" className="guest-button guest-button--terracotta guest-auth__submit">
                {t(isRegistering ? "Créer mon compte" : "Se connecter")}
              </button>
            </form>
            {!isRegistering && (
              <div className="guest-auth__demo">
                <strong>{t("Comptes de démonstration")}</strong>
                <p>{t("Choisissez un compte pour remplir son adresse e-mail. Le mot de passe est fourni lors du seed local.")}</p>
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
