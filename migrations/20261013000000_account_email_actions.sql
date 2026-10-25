create table public.account_action_tokens (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references public.users (id) on delete cascade,
    token_hash char(64) not null unique,
    purpose varchar(32) not null,
    expires_at timestamptz not null,
    used_at timestamptz,
    created_at timestamptz not null default now(),
    constraint account_action_tokens_purpose_check
        check (purpose in ('email_verification', 'password_reset'))
);

create index ix_account_action_tokens_user_id
    on public.account_action_tokens (user_id);
create index ix_account_action_tokens_user_purpose_created
    on public.account_action_tokens (user_id, purpose, created_at desc);

alter table public.account_action_tokens enable row level security;
