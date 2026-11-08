import { useEffect, useState, type FormEvent } from "react";
import {
  ArrowUpRight,
  BriefcaseBusiness,
  Building2,
  ChevronDown,
  ClipboardList,
  Compass,
  ClipboardCheck,
  GraduationCap,
  Search,
  Bookmark,
  CalendarClock,
  Bell,
  ChartNoAxesCombined,
  LayoutDashboard,
  LogOut,
  Menu,
  MessageCircle,
  Moon,
  Settings2,
  Sparkles,
  Sun,
  UserRound,
  X,
} from "lucide-react";
import { Badge, Button, Card, ProgressBar } from "./components/ui";
import { FloatingAssistant } from "./components/FloatingAssistant";
import {
  AdminDashboardPage,
  CandidateApplicationsPage,
  CandidateCoursesPage,
  EmployerApplicationsPage,
  EmployerDashboardPage,
  EmployerOrganisationPage,
  EmployerCandidatesPage,
  EmployerTalentPoolsPage,
  EmployerMessagesPage,
  EmployerInterviewsPage,
  EmployerNotificationsPage,
  EmployerAnalyticsPage,
  AdminOrganisationVerificationPage,
  CandidateInterviewsPage,
  TrainingProviderDashboardPage,
} from "./marketplace";
import {
  CandidateInterviewPreparationPage,
  CandidateMatchesPage,
  CandidateProfilePage,
  CandidateRoadmapPage,
  EmployerOffersPage,
} from "./workspaces";
import {
  ApiError,
  fetchCurrentUser,
  applyToJob,
  login,
  registerCandidate,
  type AuthUser,
  type Role,
} from "./auth";
import { GuestDiscovery } from "./GuestDiscovery";
import { GuestAuth } from "./GuestAuth";
import { ProfessionalServicesPage } from "./ProfessionalServices";
import { MissionsWorkspace } from "./MissionsWorkspace";
import { ServiceRequestsWorkspace } from "./ServiceRequestsWorkspace";
import { UnifiedAssistantWorkspace } from "./UnifiedAssistantWorkspace";

const roleConfiguration: Record<
  Role,
  {
    label: string;
    navigation: { label: string; icon: typeof LayoutDashboard }[];
    dashboardTitle: string;
    dashboardDescription: string;
  }
> = {
  candidate: {
    label: "Candidat",
    navigation: [
      { label: "Vue d’ensemble", icon: LayoutDashboard },
      { label: "Mes opportunités", icon: BriefcaseBusiness },
      { label: "Mon parcours", icon: Compass },
      { label: "Préparer un entretien", icon: ClipboardCheck },
      { label: "Formations", icon: GraduationCap },
      { label: "Mes candidatures", icon: ClipboardList },
      { label: "Mes entretiens", icon: CalendarClock },
      { label: "Assistant", icon: MessageCircle },
      { label: "Mon profil", icon: UserRound },
    ],
    dashboardTitle: "Votre espace candidat",
    dashboardDescription: "Vos compétences ouvrent des portes vers des emplois et des formations.",
  },
  employer: {
    label: "Employeur",
    navigation: [
      { label: "Vue d’ensemble", icon: LayoutDashboard },
      { label: "Mes offres", icon: BriefcaseBusiness },
      { label: "Candidatures", icon: UserRound },
      { label: "Trouver des candidats", icon: Search },
      { label: "Talents sauvegardés", icon: Bookmark },
      { label: "Messages", icon: MessageCircle },
      { label: "Entretiens", icon: CalendarClock },
      { label: "Notifications", icon: Bell },
      { label: "Statistiques", icon: ChartNoAxesCombined },
      { label: "Assistant", icon: MessageCircle },
      { label: "Mon organisation", icon: Building2 },
    ],
    dashboardTitle: "Votre espace employeur",
    dashboardDescription: "Gérez les offres de votre organisation et suivez les candidatures reçues.",
  },
  ministry_admin: {
    label: "Administration",
    navigation: [{ label: "Vue d’ensemble", icon: LayoutDashboard },
      { label: "Vérifications organisations", icon: Building2 },
      { label: "Assistant", icon: MessageCircle },
    ],
    dashboardTitle: "Espace administration",
    dashboardDescription: "Suivez les indicateurs agrégés de la plateforme et les résultats déclarés.",
  },
  training_provider: {
    label: "Organisme de formation",
    navigation: [
      { label: "Vue d’ensemble", icon: LayoutDashboard },
      { label: "Catalogue de formations", icon: GraduationCap },
      { label: "Assistant", icon: MessageCircle },
    ],
    dashboardTitle: "Espace organisme de formation",
    dashboardDescription: "Gérez votre catalogue de formations liées aux compétences validées.",
  },
  operator: {
    label: "Opérations",
    navigation: [
      { label: "Vue d’ensemble", icon: LayoutDashboard },
      { label: "Services", icon: Settings2 },
      { label: "Journaux d’audit", icon: ClipboardList },
      { label: "Assistant", icon: MessageCircle },
    ],
    dashboardTitle: "Espace opérations",
    dashboardDescription: "Suivez les services et journaux sans accéder aux données personnelles.",
  },
};

export default function App() {
  const [activePage, setActivePage] = useState("Vue d’ensemble");
  const [menuOpen, setMenuOpen] = useState(false);
  const [theme, setTheme] = useState<"light" | "dark">("light");
  const [guestPage, setGuestPage] = useState<"discovery" | "auth">(() =>
    window.location.hash === "#guest-auth" || window.location.hash === "#guest-auth-signup"
      ? "auth"
      : "discovery",
  );
  const [isRegistering, setIsRegistering] = useState(
    () => window.location.hash === "#guest-auth-signup",
  );
  const [accessToken, setAccessToken] = useState<string | null>(() =>
    sessionStorage.getItem("mahara-match-token"),
  );
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(Boolean(accessToken));
  const [authError, setAuthError] = useState("");
  const isDashboard = activePage === "Vue d’ensemble";

  useEffect(() => {
    function syncGuestRoute() {
      const authRoute =
        window.location.hash === "#guest-auth" ||
        window.location.hash === "#guest-auth-signup";
      setGuestPage(authRoute ? "auth" : "discovery");
      setIsRegistering(window.location.hash === "#guest-auth-signup");
    }

    window.addEventListener("hashchange", syncGuestRoute);
    return () => window.removeEventListener("hashchange", syncGuestRoute);
  }, []);

  useEffect(() => {
    if (!user) return;
    const syncAssistantRoute = () => {
      const hash = window.location.hash;
      const projectMatch = hash.match(/^#assistant\/project\/([^/?#]+)/);
      if (projectMatch) {
        if (user.role !== "employer") {
          window.location.hash = "#assistant";
        }
        setActivePage("Assistant");
      } else if (hash === "#assistant") {
        setActivePage("Assistant");
      }
    };
    syncAssistantRoute();
    window.addEventListener("hashchange", syncAssistantRoute);
    return () => window.removeEventListener("hashchange", syncAssistantRoute);
  }, [user]);

  useEffect(() => {
    if (!accessToken) {
      setIsLoading(false);
      return;
    }

    let cancelled = false;
    fetchCurrentUser(accessToken)
      .then((authenticatedUser) => {
        if (!cancelled) {
          setUser(authenticatedUser);
          if (!user) {
            setActivePage(roleConfiguration[authenticatedUser.role].navigation[0].label);
          }
          setIsLoading(false);
        }
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        if (error instanceof ApiError && error.status === 401) {
          sessionStorage.removeItem("mahara-match-token");
          setAccessToken(null);
        }
        setAuthError(
          error instanceof ApiError
            ? error.message
            : "Impossible de joindre le service. Vérifiez votre connexion.",
        );
        setIsLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [accessToken]);

  async function handleAuthentication(
    event: FormEvent<HTMLFormElement>,
    email: string,
    password: string,
    isRegistration: boolean,
  ) {
    event.preventDefault();
    setAuthError("");
    try {
      const result = isRegistration
        ? await registerCandidate(email, password)
        : await login(email, password);
      sessionStorage.setItem("mahara-match-token", result.access_token);
      setAccessToken(result.access_token);
      setUser(result.user);
      let destination = isRegistration
        ? "Mon profil"
        : roleConfiguration[result.user.role].navigation[0].label;
      const pendingOfferId = sessionStorage.getItem("mahara-match-return-job");
      if (pendingOfferId && result.user.role === "candidate") {
        try {
          await applyToJob(result.access_token, pendingOfferId);
          sessionStorage.removeItem("mahara-match-return-job");
          sessionStorage.removeItem("mahara-match-return-job-title");
          destination = "Mes candidatures";
        } catch (error: unknown) {
          setAuthError(error instanceof ApiError ? error.message : "Impossible de reprendre votre candidature.");
          destination = "Mes opportunités";
        }
      } else if (pendingOfferId && result.user.role !== "candidate") {
        setAuthError("Connectez-vous avec un compte candidat pour postuler à cette offre.");
      }
      if (sessionStorage.getItem("mahara-match-return-service")) {
        destination = "Mes demandes";
        sessionStorage.removeItem("mahara-match-return-service");
        sessionStorage.removeItem("mahara-match-return-service-title");
      }
      setActivePage(destination);
    } catch (error: unknown) {
      setAuthError(
        error instanceof ApiError
          ? error.message
          : "Impossible de joindre le service. Vérifiez votre connexion.",
      );
    }
  }

  function handleLogout() {
    sessionStorage.removeItem("mahara-match-token");
    setAccessToken(null);
    setUser(null);
    setAuthError("");
    setActivePage("Vue d’ensemble");
  }

  if (isLoading) {
    return (
      <div className="app-shell" data-theme={theme}>
        <main className="auth-page" aria-live="polite">
          <p>Vérification de votre session…</p>
        </main>
      </div>
    );
  }

  if (!user || !accessToken) {
    const pendingOfferTitle = sessionStorage.getItem("mahara-match-return-job-title");
    const pendingServiceTitle = sessionStorage.getItem("mahara-match-return-service-title");
    const pendingNote = pendingOfferTitle
      ? `Connectez-vous pour postuler à « ${pendingOfferTitle} »`
      : pendingServiceTitle
        ? `Connectez-vous pour demander « ${pendingServiceTitle} »`
        : "";
    return (
      <div className="app-shell" data-theme={theme}>
        {guestPage === "discovery" ? (
          <GuestDiscovery
            onApply={(offer) => {
              sessionStorage.setItem("mahara-match-return-job", offer.id);
              sessionStorage.setItem("mahara-match-return-job-title", offer.title);
              window.location.hash = "#guest-auth";
            }}
            onRequestService={(service) => {
              sessionStorage.setItem("mahara-match-return-service", service.id);
              sessionStorage.setItem("mahara-match-return-service-title", service.title);
              window.location.hash = "#guest-auth";
            }}
          />
        ) : (
          <GuestAuth
            error={authError}
            isRegistering={isRegistering}
            pendingNote={pendingNote}
            onModeChange={(registering) => {
              window.location.hash = registering ? "#guest-auth-signup" : "#guest-auth";
            }}
            onAuthenticate={handleAuthentication}
          />
        )}
      </div>
    );
  }

  const configuration = roleConfiguration[user.role];
  const isCandidate = user.role === "candidate";
  const assistantRoute = window.location.hash.match(/^#assistant(?:\/project\/([^/?#]+))?/);
  const assistantProjectId = assistantRoute?.[1];


  return (
    <div className={`app-shell ${activePage === "Assistant" ? "app-shell--assistant" : ""}`} data-theme={theme}>
      <aside className={`sidebar ${menuOpen ? "sidebar--open" : ""}`}>
        <div className="brand-row">
          <a
            className="brand"
            href="#accueil"
            aria-label="Mahara Match, accueil"
            onClick={() => setActivePage("Vue d’ensemble")}
          >
            <span className="brand__mark" aria-hidden="true">
              m
            </span>
            <span className="brand__name">
              mahara<span>match</span>
            </span>
          </a>
          <button
            className="icon-button sidebar__close"
            type="button"
            aria-label="Fermer le menu"
            onClick={() => setMenuOpen(false)}
          >
            <X size={20} />
          </button>
        </div>

        <div className="sidebar__label">ESPACE {configuration.label.toLocaleUpperCase("fr-FR")}</div>
        <nav className="nav-list" aria-label="Navigation principale">
          {configuration.navigation.map(({ label, icon: Icon }) => (
            <button
              className={`nav-item ${activePage === label ? "nav-item--active" : ""}`}
              key={label}
              type="button"
              aria-label={label}
              aria-current={activePage === label ? "page" : undefined}
              onClick={() => {
                setActivePage(label);
                setMenuOpen(false);
                if (label === "Assistant") window.location.hash = "#assistant";
              }}
            >
              <Icon size={19} strokeWidth={1.8} aria-hidden="true" />
              <span>{label}</span>
              {isCandidate && label === "Assistant" && (
                <span className="nav-item__new">Nouveau</span>
              )}
            </button>
          ))}
        </nav>

        {isCandidate && (
          <Card className="sidebar-tip">
            <span className="sidebar-tip__icon">
              <Sparkles size={17} aria-hidden="true" />
            </span>
            <strong>Vos compétences ouvrent des portes.</strong>
            <p>Complétez votre profil pour découvrir les prochaines étapes.</p>
            <Button
              variant="secondary"
              className="sidebar-tip__button"
              onClick={() => setActivePage("Mon profil")}
            >
              Compléter mon profil <ArrowUpRight size={15} aria-hidden="true" />
            </Button>
          </Card>
        )}

        <div className="account-switcher">
          <span className="avatar" aria-hidden="true">
            {configuration.label.slice(0, 1)}
          </span>
          <span className="account-switcher__text">
            <strong>{user.email}</strong>
            <small>{configuration.label}</small>
          </span>
          <ChevronDown size={16} aria-hidden="true" />
        </div>
      </aside>

      {menuOpen && (
        <button
          className="sidebar-scrim"
          type="button"
          aria-label="Fermer le menu"
          onClick={() => setMenuOpen(false)}
        />
      )}

      <main className="main-area">
        <header className="topbar">
          <button
            className="icon-button menu-toggle"
            type="button"
            aria-label="Ouvrir le menu"
            onClick={() => setMenuOpen(true)}
          >
            <Menu size={21} />
          </button>
          <div className="breadcrumbs">
            <span>Mon espace</span>
            <span aria-hidden="true">/</span>
            <strong>{activePage}</strong>
          </div>
          <div className="topbar__actions">
            {user.role !== "candidate" && <button className="professional-profile-link" type="button" onClick={() => setActivePage("Profil professionnel")}>Profil professionnel</button>}
            <button className="professional-profile-link" type="button" onClick={() => setActivePage("Missions")}>Missions</button>
            <button className="professional-profile-link" type="button" onClick={() => setActivePage("Mes demandes")}>Mes demandes</button>
            <button
              className="icon-button"
              type="button"
              aria-label={theme === "light" ? "Activer le thème sombre" : "Activer le thème clair"}
              onClick={() => setTheme(theme === "light" ? "dark" : "light")}
            >
              {theme === "light" ? <Moon size={18} /> : <Sun size={18} />}
            </button>
            <span className="topbar__divider" />
            <span className="avatar avatar--small" aria-hidden="true">
              {configuration.label.slice(0, 1)}
            </span>
            <span className="topbar__account">{configuration.label}</span>
            <button className="icon-button" type="button" aria-label="Se déconnecter" onClick={handleLogout}>
              <LogOut size={18} />
            </button>
          </div>
        </header>

        <div className="page-content">
          {isDashboard ? (
            isCandidate ? (
              <Dashboard onNavigate={setActivePage} />
            ) : user.role === "ministry_admin" ? (
              <AdminDashboardPage token={accessToken} />
            ) : user.role === "training_provider" ? (
              <TrainingProviderDashboardPage token={accessToken} />
            ) : user.role === "employer" ? (
              <EmployerDashboardPage token={accessToken} onNavigate={setActivePage} />
            ) : (
              <RoleDashboard
                title={configuration.dashboardTitle}
                description={configuration.dashboardDescription}
                role={configuration.label}
                onNavigate={setActivePage}
              />
            )
          ) : user.role !== "candidate" && activePage === "Profil professionnel" ? (
            <ProfessionalServicesPage token={accessToken} />
          ) : activePage === "Missions" ? (
            <MissionsWorkspace token={accessToken} />
          ) : activePage === "Mes demandes" ? (
            <ServiceRequestsWorkspace token={accessToken} userId={user.id} />
          ) : isCandidate && activePage === "Mon profil" ? (
            <>
              <CandidateProfilePage token={accessToken} />
              <ProfessionalServicesPage token={accessToken} />
            </>
          ) : isCandidate && activePage === "Mes opportunités" ? (
            <CandidateMatchesPage token={accessToken} onNavigate={setActivePage} />
          ) : isCandidate && activePage === "Mon parcours" ? (
            <CandidateRoadmapPage token={accessToken} onNavigate={setActivePage} />
          ) : isCandidate && activePage === "Préparer un entretien" ? (
            <CandidateInterviewPreparationPage token={accessToken} onNavigate={setActivePage} />
          ) : activePage === "Assistant" ? (
            <UnifiedAssistantWorkspace token={accessToken} role={user.role} projectId={assistantProjectId} />
          ) : isCandidate && activePage === "Formations" ? (
            <CandidateCoursesPage token={accessToken} />
          ) : isCandidate && activePage === "Mes candidatures" ? (
            <CandidateApplicationsPage token={accessToken} />
          ) : isCandidate && activePage === "Mes entretiens" ? (
            <CandidateInterviewsPage token={accessToken} />
          ) : user.role === "employer" && activePage === "Mes offres" ? (
            <EmployerOffersPage token={accessToken} />
          ) : user.role === "employer" && activePage === "Candidatures" ? (
            <EmployerApplicationsPage token={accessToken} onNavigate={setActivePage} />
          ) : user.role === "employer" && activePage === "Mon organisation" ? (
            <EmployerOrganisationPage token={accessToken} />
          ) : user.role === "employer" && activePage === "Trouver des candidats" ? (
            <EmployerCandidatesPage token={accessToken} />
          ) : user.role === "employer" && activePage === "Talents sauvegardés" ? (
            <EmployerTalentPoolsPage token={accessToken} />
          ) : user.role === "employer" && activePage === "Messages" ? (
            <EmployerMessagesPage token={accessToken} />
          ) : user.role === "employer" && activePage === "Entretiens" ? (
            <EmployerInterviewsPage token={accessToken} />
          ) : user.role === "employer" && activePage === "Notifications" ? (
            <EmployerNotificationsPage token={accessToken} />
          ) : user.role === "employer" && activePage === "Statistiques" ? (
            <EmployerAnalyticsPage token={accessToken} />
          ) : user.role === "ministry_admin" && activePage === "Vérifications organisations" ? (
            <AdminOrganisationVerificationPage token={accessToken} />
          ) : user.role === "training_provider" && activePage === "Catalogue de formations" ? (
            <TrainingProviderDashboardPage token={accessToken} />
          ) : (
            <section className="page-placeholder">
              <Badge>En préparation</Badge>
              <h1>{activePage}</h1>
              <p>
                Cet espace n’est pas encore disponible. Aucune information n’est
                simulée ; vos données apparaîtront ici lorsque la fonctionnalité
                sera prête.
              </p>
              <Button variant="secondary" onClick={() => setActivePage("Vue d’ensemble")}>
                Retour à la vue d’ensemble
              </Button>
            </section>
          )}
        </div>
      </main>
      {activePage !== "Assistant" && (
        <FloatingAssistant
          token={accessToken}
          onExpand={() => {
            window.location.hash = "#assistant";
            setActivePage("Assistant");
          }}
        />
      )}
    </div>
  );
}

function RoleDashboard({
  title,
  description,
  role,
  onNavigate,
}: {
  title: string;
  description: string;
  role: string;
  onNavigate: (page: string) => void;
}) {
  return (
    <section className="role-dashboard">
      <div className="eyebrow">{role.toLocaleUpperCase("fr-FR")}</div>
      <h1>{title}</h1>
      <p className="role-dashboard__description">{description}</p>
      <Card className="role-dashboard__empty">
        {role === "Employeur" ? (
          <>
            <Badge>Gestion des offres</Badge>
            <h2>Publiez une offre pour trouver les bons profils</h2>
            <p>Décrivez le poste et ses compétences clés pour la proposer aux candidats.</p>
            <Button onClick={() => onNavigate("Mes offres")}>Créer une offre</Button>
          </>
        ) : (
          <>
            <Badge>En préparation</Badge>
            <h2>Votre espace est prêt à être configuré</h2>
            <p>
              Les fonctions de ce rôle ne sont pas encore disponibles. Aucune offre,
              candidature, formation ou statistique n’est simulée.
            </p>
          </>
        )}
      </Card>
    </section>
  );
}

function Dashboard({ onNavigate }: { onNavigate: (page: string) => void }) {
  return (
    <>
      <section className="welcome-row">
        <div>
          <div className="eyebrow">
            {new Intl.DateTimeFormat("fr-FR", {
              weekday: "long",
              day: "numeric",
              month: "long",
            }).format(new Date()).toLocaleUpperCase("fr-FR")}
          </div>
          <h1>Bonjour et bienvenue</h1>
          <p className="welcome-row__subtitle">
            Votre prochain projet professionnel commence ici.
          </p>
        </div>
        <Button onClick={() => onNavigate("Mon profil")}>
          <UserRound size={17} aria-hidden="true" />
          Compléter mon profil
        </Button>
      </section>

      <section className="profile-card" aria-labelledby="profile-title">
        <div className="profile-card__content">
          <div className="profile-card__heading">
            <div>
              <div className="eyebrow eyebrow--light">VOTRE PROFIL</div>
              <h2 id="profile-title">Faites briller vos compétences</h2>
            </div>
            <div className="profile-score" aria-label="Profil à compléter">
              <span>—</span>
              <small>à compléter</small>
            </div>
          </div>
          <p>
            Quelques informations suffisent pour commencer à explorer des
            opportunités qui vous ressemblent.
          </p>
          <div className="profile-card__footer">
            <div className="profile-progress">
              <div className="profile-progress__label">
                <span>Profil en cours de création</span>
                <span>Ajoutez vos premières informations</span>
              </div>
              <ProgressBar value={0} label="Profil en cours de création" />
            </div>
            <Button variant="light" onClick={() => onNavigate("Mon profil")}>
              Démarrer <ArrowUpRight size={16} aria-hidden="true" />
            </Button>
          </div>
        </div>
        <div className="profile-card__art" aria-hidden="true">
          <div className="orbit orbit--one" />
          <div className="orbit orbit--two" />
          <div className="art-spark art-spark--one">✳</div>
          <div className="art-spark art-spark--two">✦</div>
          <div className="art-center">
            <span>m</span>
            <i />
          </div>
        </div>
      </section>

      <section className="section-heading">
        <div>
          <div className="eyebrow">VOTRE ESPACE</div>
          <h2>Un premier pas à la fois</h2>
        </div>
        <Badge tone="accent">Bienvenue</Badge>
      </section>

      <section className="overview-grid" aria-label="Aperçu de votre espace">
        <Card className="overview-card">
          <div className="overview-card__top">
            <span className="overview-icon overview-icon--blue">
              <BriefcaseBusiness size={19} aria-hidden="true" />
            </span>
            <span className="overview-card__arrow" aria-hidden="true">
              <ArrowUpRight size={17} />
            </span>
          </div>
          <h3>Opportunités</h3>
          <p>Vos pistes professionnelles apparaîtront ici lorsque votre profil sera prêt.</p>
          <button className="text-link" type="button" onClick={() => onNavigate("Mes opportunités")}>
            En savoir plus <ArrowUpRight size={14} aria-hidden="true" />
          </button>
        </Card>

        <Card className="overview-card">
          <div className="overview-card__top">
            <span className="overview-icon overview-icon--mint">
              <Compass size={19} aria-hidden="true" />
            </span>
            <span className="overview-card__arrow" aria-hidden="true">
              <ArrowUpRight size={17} />
            </span>
          </div>
          <h3>Mon parcours</h3>
          <p>Explorez des étapes adaptées à votre expérience après avoir renseigné vos compétences.</p>
          <button className="text-link" type="button" onClick={() => onNavigate("Mon parcours")}>
            En savoir plus <ArrowUpRight size={14} aria-hidden="true" />
          </button>
        </Card>

        <Card className="assistant-card">
          <span className="assistant-card__glow" aria-hidden="true" />
          <div className="assistant-card__icon">
            <Sparkles size={20} aria-hidden="true" />
          </div>
          <Badge tone="accent">À votre rythme</Badge>
          <h3>Besoin d’un coup de main ?</h3>
          <p>Obtenez des conseils pour valoriser vos compétences et mieux explorer les offres.</p>
          <Button
            variant="secondary"
            className="assistant-card__button"
            onClick={() => onNavigate("Assistant")}
          >
            Découvrir l’assistant <ArrowUpRight size={15} aria-hidden="true" />
          </Button>
        </Card>
      </section>

      <footer className="page-footer">
        <span>Mahara Match</span>
        <span>Vos compétences, votre avenir.</span>
      </footer>
    </>
  );
}
