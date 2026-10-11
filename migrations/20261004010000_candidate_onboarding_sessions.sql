create table public.candidate_onboarding_sessions (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references public.users (id) on delete cascade,
    answers jsonb not null default '{}'::jsonb,
    status varchar(20) not null default 'active',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint candidate_onboarding_sessions_status_check
        check (status in ('active', 'completed'))
);

create index candidate_onboarding_sessions_user_idx
    on public.candidate_onboarding_sessions (user_id, created_at desc);