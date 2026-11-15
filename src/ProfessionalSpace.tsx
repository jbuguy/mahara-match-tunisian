import { useEffect, useState } from "react";
import { BriefcaseBusiness, Sparkles } from "lucide-react";
import { ApiError, fetchCandidateProfile, fetchMyProfessionalProfile, type CandidateAssistantProfessionalSuggestion, type CandidateProfile, type ProfessionalProfile } from "./auth";
import { CandidateProfilePage } from "./workspaces";
import { ProfessionalServicesPage } from "./ProfessionalServices";
import { Card } from "./components/ui";

type ProfessionalSummary = {
  candidate: CandidateProfile;
  professional: ProfessionalProfile | null;
};

const emptySummary: ProfessionalSummary | null = null;

export function ProfessionalSpacePage({ token }: { token: string }) {
  const [summary, setSummary] = useState<ProfessionalSummary | null>(emptySummary);
  const [sharedSkills, setSharedSkills] = useState<string[]>([]);
  const [persistedSkills, setPersistedSkills] = useState<string[]>([]);
  const [assistantDraftEvents, setAssistantDraftEvents] = useState<CandidateAssistantProfessionalSuggestion[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      fetchCandidateProfile(token),
      fetchMyProfessionalProfile(token).catch((cause: unknown) => {
        if (cause instanceof ApiError && cause.status === 404) return null;
        throw cause;
      }),
    ]).then(([candidate, professional]) => {
      if (!cancelled) {
        const normalizedProfessional = professional && isProfessionalProfile(professional) ? professional : null;
        const normalizedCandidate = {
            ...candidate,
            skills: Array.isArray(candidate.skills) ? candidate.skills : [],
            education_entries: Array.isArray(candidate.education_entries) ? candidate.education_entries : [],
            experience_entries: Array.isArray(candidate.experience_entries) ? candidate.experience_entries : [],
          };
        const mergedSkills = [...new Set([...normalizedCandidate.skills, ...(normalizedProfessional?.skills ?? [])])];
        setSharedSkills(mergedSkills);
        setPersistedSkills(mergedSkills);
        setSummary({ candidate: normalizedCandidate, professional: normalizedProfessional });
      }
    }).catch((cause: unknown) => {
      if (!cancelled) setError(cause instanceof ApiError ? cause.message : "Impossible de charger votre espace professionnel.");
    }).finally(() => {
      if (!cancelled) setLoading(false);
    });
    return () => { cancelled = true; };
  }, [token]);

  const headline = summary?.professional?.headline || summary?.candidate.professional_headline;
  const skills = [...new Set(sharedSkills)];
  const location = summary?.candidate.location || summary?.professional?.location;
  const displayName = summary?.candidate.full_name || summary?.professional?.display_name || "Votre nom";
  const initials = displayName.split(/\s+/).filter(Boolean).slice(0, 2).map((part) => part[0]).join("").toLocaleUpperCase();
  const completeness = summary ? calculateCompleteness(summary, sharedSkills) : { percentage: 0, missing: [] as string[] };

  return <main className="professional-space-page">
    <header className="professional-space-page__heading">
      <div className="eyebrow">ESPACE PROFESSIONNEL</div>
      <h1>Mon espace professionnel</h1>
      <p>Gérez votre profil, valorisez vos compétences, trouvez un emploi et proposez vos services.</p>
      <nav aria-label="Professional space sections">
        <a href="#candidate-profile"><BriefcaseBusiness size={16} /> Trouver un emploi</a>
        <a href="#professional-services"><Sparkles size={16} /> Proposer mes services</a>
      </nav>
    </header>

    {error && <p className="workspace-error" role="alert">{error}</p>}
    {loading ? <p aria-live="polite">Chargement de votre espace professionnel…</p> : summary && <>
      <Card className="professional-space-overview">
        <div className="professional-space-overview__identity">
          {summary.professional?.photo_url
            ? <img src={summary.professional.photo_url} alt="" />
            : <span className="professional-space-overview__avatar" aria-hidden="true">{initials || "?"}</span>}
          <div>
            <h2>{displayName}</h2>
            {headline && <p className="professional-space-overview__headline">{headline}</p>}
            {location && <p>{location}</p>}
            {summary.professional?.introduction && <p>{summary.professional.introduction}</p>}
          </div>
        </div>
        <div className="professional-space-overview__completeness">
          <div><strong>Profil complété</strong><span>{completeness.percentage}%</span></div>
          <progress max={100} value={completeness.percentage} aria-label={`Profil complété à ${completeness.percentage}%`} />
          {completeness.missing.length > 0 && <p>Prochaines étapes : {completeness.missing.join(", ")}.</p>}
          {skills.length > 0 && <div className="professional-space-overview__skills">{skills.map((skill) => <span key={skill}>{skill}</span>)}</div>}
        </div>
      </Card>

      <section className="professional-space-activities" aria-labelledby="professional-space-activities-title">
        <h2 id="professional-space-activities-title">Que souhaitez-vous faire ?</h2>
        <p>Vous pouvez rechercher un emploi et proposer vos services en même temps.</p>
        <div>
          <a href="#candidate-profile"><BriefcaseBusiness size={18} /><span><strong>Rechercher un emploi</strong><small>Gérez votre profil et sa visibilité auprès des recruteurs.</small></span></a>
          <a href="#professional-services"><Sparkles size={18} /><span><strong>Proposer des services</strong><small>Créez vos services et gérez leur publication.</small></span></a>
        </div>
      </section>

      <CandidateProfilePage token={token} embedded sharedSkills={sharedSkills} persistedSkills={persistedSkills} onSharedSkillsChange={setSharedSkills} onSharedSkillsSaved={setPersistedSkills} onProfessionalSuggestionApply={(suggestion) => setAssistantDraftEvents((current) => [...current, suggestion])} />
      <ProfessionalServicesPage token={token} embedded sharedSkills={sharedSkills} persistedSkills={persistedSkills} onSharedSkillsChange={setSharedSkills} onSharedSkillsSaved={setPersistedSkills} assistantDraftEvents={assistantDraftEvents} />
    </>}
  </main>;
}

function calculateCompleteness({ candidate, professional }: ProfessionalSummary, skills: string[]): { percentage: number; missing: string[] } {
  const checks: [string, boolean][] = [
    ["Ajoutez votre nom", hasText(candidate.full_name) || hasText(professional?.display_name)],
    ["Ajoutez un titre professionnel", hasText(professional?.headline) || hasText(candidate.professional_headline)],
    ["Rédigez une présentation", hasText(professional?.introduction)],
    ["Ajoutez votre lieu de résidence", hasText(candidate.location) || Boolean(candidate.governorate_code) || hasText(professional?.location)],
    ["Ajoutez au moins une compétence", skills.length > 0],
    ["Ajoutez une langue", (professional?.languages.length ?? 0) > 0],
    ["Ajoutez une formation", candidate.education_entries.length > 0 || hasText(candidate.education)],
    ["Ajoutez un élément de portfolio", (professional?.portfolio_items.length ?? 0) > 0],
  ];
  const complete = checks.filter(([, done]) => done).length;
  return {
    percentage: Math.round((complete / checks.length) * 100),
    missing: checks.filter(([, done]) => !done).map(([label]) => label),
  };
}

function isProfessionalProfile(value: ProfessionalProfile): boolean {
  return typeof value.display_name === "string"
    && typeof value.headline === "string"
    && typeof value.introduction === "string"
    && Array.isArray(value.skills)
    && Array.isArray(value.languages)
    && Array.isArray(value.portfolio_items)
    && Array.isArray(value.service_area)
    && typeof value.availability === "object"
    && value.availability !== null;
}

function hasText(value: string | null | undefined): boolean {
  return typeof value === "string" && value.trim().length > 0;
}
