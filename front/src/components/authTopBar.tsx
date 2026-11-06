import { Link } from "react-router-dom";
import { useI18n } from "../lib/i18n";

type Props = {
    /** Which cross-link to show: "signin" shows "Sign in", "signup" shows "Sign up". */
    cta: "signin" | "signup";
    role?: "candidate" | "employer";
};

const copy = {
    fr: {
        haveAccount: "Vous avez déjà un compte ?",
        noAccount: "Nouveau sur la plateforme ?",
    },
    en: {
        haveAccount: "Already have an account?",
        noAccount: "New to the platform?",
    },
    ar: { haveAccount: "لديك حساب؟", noAccount: "جديد على المنصة؟" },
} as const;

/** One header used by both the sign-in and sign-up pages. */
export function AuthTopBar({ cta, role }: Props) {
    const { language, setLanguage, t } = useI18n();
    const text = copy[language as keyof typeof copy] ?? copy.fr;

    return (
        <>
            <header className="auth-topbar">
                <Link to="/signup" className="auth-brand">
                    <span className="auth-brand-mark" aria-hidden="true">
                        ••
                        <br />
                        ••
                    </span>
                    <span className="auth-brand-text">
                        <strong>Mahara Match · مهارة ماتش</strong>
                        <small>{t("brand.platform")}</small>
                    </span>
                </Link>
                <nav className="auth-topbar-actions" aria-label="navigation">
                    <div
                        className="lang-switch"
                        role="group"
                        aria-label="Language"
                    >
                        {(
                            [
                                ["fr", "Français"],
                                ["en", "English"],
                                ["ar", "العربية"],
                            ] as const
                        ).map(([code, label]) => (
                            <button
                                key={code}
                                type="button"
                                className={language === code ? "selected" : ""}
                                aria-pressed={language === code}
                                onClick={() => setLanguage(code)}
                            >
                                {label}
                            </button>
                        ))}
                    </div>
                    <div className="auth-topbar-cta">
                        <span>
                            {cta === "signin"
                                ? text.haveAccount
                                : text.noAccount}
                        </span>
                        {cta === "signin" ? (
                            <Link to="/signin">{t("nav.signIn")}</Link>
                        ) : (
                            <Link to={`/signup${role ? `?role=${role}` : ""}`}>
                                {t("auth.signUp")}
                            </Link>
                        )}
                    </div>
                </nav>
            </header>
        </>
    );
}
