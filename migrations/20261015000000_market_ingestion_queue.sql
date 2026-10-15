-- Durable ministry market refresh requests and replay protection.
alter table public.ingestion_jobs
    add column if not exists request_data jsonb not null default '{}'::jsonb,
    add column if not exists idempotency_key varchar(128);

create unique index if not exists ingestion_jobs_idempotency_key_uq
    on public.ingestion_jobs (idempotency_key)
    where idempotency_key is not null;

create index if not exists ingestion_jobs_pending_market_idx
    on public.ingestion_jobs (created_at)
    where source = 'ministry_market' and status = 'pending';
