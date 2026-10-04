export type TaxonomyStatus = "draft" | "validated" | "deprecated";
export type SkillType = "hard" | "soft" | "language";

/** Mirrors WP1's SkillRead contract. */
export type Skill = {
  skill_id: string;
  code: string;
  label_fr: string;
  label_ar: string | null;
  label_derja: string | null;
  alt_labels: string[];
  skill_type: SkillType;
  status: TaxonomyStatus;
  esco_uri: string | null;
  version: number;
};

export type Dependency = { name: string; status: string; detail?: string | null };
export type Readiness = { status: string; module: string; dependencies: Dependency[] };