export type InterviewMode = 'chat' | 'form';

export interface ChatMessage {
  role: 'assistant' | 'user';
  content: string;
}

export interface JobSkill {
  skill_code: string;
  requirement: 'required' | 'preferred';
  min_level: number;
}

export interface OfferDraft {
  offer_id?: string | null;
  title: string;
  description: string;
  occupation_code: string | null;
  contract_type: string;
  work_mode: string;
  location: { governorate_code: string; delegation?: string | null };
  positions_count: number;
  min_years_experience: number;
  education_level_min: string | null;
  salary: { min_tnd: number | null; max_tnd: number | null; period: 'hour' | 'day' | 'month' } | null;
  skills: JobSkill[];
  languages_required: { code: string; level: number }[];
  status: 'draft' | 'published';
  published_at?: string | null;
  [key: string]: unknown;
}

export interface AgentSession {
  id: string;
  mode: InterviewMode;
  messages: ChatMessage[];
  answers: Record<string, string>;
  skipped: string[];
  current_field: string | null;
  complete: boolean;
  missing_fields: string[];
  draft: OfferDraft | null;
}

export interface OfferReview {
  salary: {
    status: string;
    message: string;
    comparison?: string;
    benchmark: null | {
      median_tnd: number;
      period: string | null;
      publisher: string;
      dataset: string;
      period_start: string;
      period_end: string;
    };
  };
  requirement_suggestions: { field: string; message: string }[];
  candidate_snapshot: {
    title: string;
    responsibilities: string;
    experience_years_min: number;
    education_level_min: string | null;
    location: { governorate_code: string; delegation?: string | null };
    work_mode: string;
    skills: { label: string; requirement: string; min_level: number }[];
    languages_required: { code: string; level: number }[];
  };
}

export async function apiRequest<T>(path: string, token: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set('Authorization', `Bearer ${token}`);
  if (init.body && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json');
  const response = await fetch(path, { ...init, headers });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const detail = body?.detail;
    throw new Error(typeof detail === 'string' ? detail : 'Une erreur est survenue. Réessayez.');
  }
  return response.json() as Promise<T>;
}

export function explainError(error: unknown): string {
  return error instanceof Error ? error.message : 'Une erreur est survenue. Réessayez.';
}