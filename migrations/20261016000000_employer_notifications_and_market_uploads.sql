alter table public.job_offers
    add column if not exists archived_at timestamptz;

alter table public.applications
    add column if not exists employer_contact_consent_at timestamptz;

create table if not exists public.notification_outbox (
    id uuid primary key default gen_random_uuid(),
    application_id uuid not null references public.applications(id) on delete cascade,
    candidate_id uuid not null references public.candidates(id) on delete cascade,
    employer_id uuid not null references public.employers(id) on delete cascade,
    meeting_at timestamptz not null,
    meeting_timezone varchar(64) not null,
    recipient_email varchar(320) not null,
    subject varchar(200) not null,
    body text not null,
    status varchar(16) not null default 'queued'
        check (status in ('queued', 'sending', 'sent', 'failed', 'cancelled')),
    attempts integer not null default 0,
    next_attempt_at timestamptz not null default now(),
    last_attempt_at timestamptz,
    last_error text,
    sent_at timestamptz,
    created_at timestamptz not null default now()
);
create index if not exists notification_outbox_due_idx
    on public.notification_outbox (next_attempt_at) where status in ('queued', 'failed');
create unique index if not exists notification_outbox_application_meeting_uq
    on public.notification_outbox (application_id, meeting_at);

create table if not exists public.market_upload_previews (
    id uuid primary key default gen_random_uuid(),
    actor_user_id uuid not null references public.users(id),
    storage_path varchar(512) not null,
    original_filename varchar(255) not null,
    mime_type varchar(100) not null,
    size_bytes bigint not null,
    sha256 varchar(64) not null,
    dataset_data jsonb not null,
    preview_data jsonb not null,
    expires_at timestamptz not null,
    dataset_id uuid references public.market_datasets(id),
    confirmed_at timestamptz,
    created_at timestamptz not null default now()
);
create index if not exists market_upload_previews_expiry_idx
    on public.market_upload_previews (expires_at);

alter table public.notification_outbox enable row level security;
alter table public.market_upload_previews enable row level security;
