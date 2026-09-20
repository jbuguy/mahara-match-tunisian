create type public.company_size as enum ('1-10', '11-50', '51-200', '200+');

create table public.employers (
    id uuid primary key default gen_random_uuid(),
    company_name text not null,
    email text not null unique,
    password_hash text not null,
    sector text not null,
    company_size public.company_size not null,
    created_at timestamptz not null default now(),
    verified boolean not null default false
);

create index employers_email_idx on public.employers (email);