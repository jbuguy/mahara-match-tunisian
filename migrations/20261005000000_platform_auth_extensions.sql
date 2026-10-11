-- Platform authentication extensions on the canonical WP1 account schema.

alter table public.users
    add column email_verified boolean not null default false,
    add column roles jsonb not null default '[]'::jsonb;

update public.users
set roles = jsonb_build_array(role::text)
where roles = '[]'::jsonb;

alter table public.candidate_pii add column photo bytea;

create table public.auth_identities (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references public.users (id) on delete cascade,
    provider varchar(16) not null,
    provider_user_id varchar(255) not null,
    email varchar(320) not null,
    email_verified boolean not null default false,
    password_hash varchar(255),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint auth_identities_provider_check check (provider in ('google', 'password')),
    constraint uq_auth_identity_user_provider unique (user_id, provider),
    constraint uq_auth_identity_provider_subject unique (provider, provider_user_id)
);

alter table public.auth_identities enable row level security;

create trigger auth_identities_set_updated_at
    before update on public.auth_identities
    for each row execute function public.set_updated_at();