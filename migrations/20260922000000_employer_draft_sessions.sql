create table public.employer_draft_sessions (
    id uuid primary key default gen_random_uuid(),
    employer_id uuid not null references public.employers(id) on delete cascade,
    state jsonb not null default '{}'::jsonb,
    messages jsonb not null default '[]'::jsonb,
    draft jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index employer_draft_sessions_employer_idx
    on public.employer_draft_sessions (employer_id, updated_at desc);