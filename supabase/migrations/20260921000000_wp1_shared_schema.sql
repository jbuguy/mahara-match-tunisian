-- WP1 Data Layer - shared schema v1.0
-- Source of truth for Python: data-layer-wp1/mahara_data/db/models
-- Keep in sync: data-layer-wp1/tests/test_migration_sync.py fails on drift.
--
-- Compatible with WP4's 20260920000000_create_employers.sql: `company_size` and
-- `employers` are created only if missing, then extended with WP1 columns.

create extension if not exists vector;

-- ---------------------------------------------------------------------------
-- Enum types
-- ---------------------------------------------------------------------------

do $$
begin
    if not exists (select 1 from pg_type where typname = 'company_size' and typnamespace = 'public'::regnamespace) then
        create type public.company_size as enum ('1-10', '11-50', '51-200', '200+');
    end if;
end
$$;

create type public.user_role as enum ('candidate', 'employer', 'admin', 'ministry', 'training_provider');
create type public.onboarding_path as enum ('cv_upload', 'derja_guided_voice', 'derja_detailed');
create type public.literacy_level as enum ('non_literate', 'basic', 'literate');
create type public.education_level as enum (
    'none', 'primary', 'lower_secondary', 'baccalaureate', 'vocational_cap', 'vocational_btp',
    'vocational_bts', 'licence', 'master', 'engineer', 'doctorate'
);
create type public.skill_type as enum ('hard', 'soft', 'language');
create type public.taxonomy_status as enum ('draft', 'validated', 'deprecated');
create type public.skill_relation_type as enum ('broader', 'related', 'equivalent');
create type public.suggestion_status as enum ('pending', 'approved', 'rejected', 'merged');
create type public.skill_source as enum ('cv', 'dialogue', 'certification', 'self_declared', 'employer_feedback');
create type public.requirement_level as enum ('required', 'preferred');
create type public.contract_type as enum (
    'cdi', 'cdd', 'sivp', 'karama', 'internship', 'freelance', 'seasonal', 'daily_work'
);
create type public.work_mode as enum ('on_site', 'remote', 'hybrid');
create type public.offer_status as enum ('draft', 'pending_review', 'published', 'closed', 'filled');
create type public.offer_source as enum ('employer_form', 'ministry_feed', 'bulk_import');
create type public.application_status as enum (
    'submitted', 'viewed', 'shortlisted', 'interview', 'offer_made', 'hired', 'rejected', 'withdrawn'
);
create type public.hiring_decision as enum ('hired', 'shortlisted', 'rejected', 'no_show');
create type public.gap_type as enum ('missing', 'insufficient_level');
create type public.roadmap_status as enum ('active', 'completed', 'abandoned');
create type public.roadmap_item_status as enum ('todo', 'in_progress', 'done', 'skipped');
create type public.course_modality as enum ('in_person', 'online', 'blended');
create type public.verification_status as enum ('pending', 'verified', 'rejected');
create type public.market_data_origin as enum ('official', 'informal', 'study');
create type public.market_indicator_type as enum (
    'job_demand', 'job_supply', 'vacancies', 'unemployment_rate', 'median_salary', 'skill_demand'
);
create type public.conversation_channel as enum ('text', 'audio');
create type public.document_type as enum (
    'cv', 'audio', 'transcript', 'certificate', 'market_dataset', 'training_catalog', 'other'
);
create type public.processing_status as enum ('pending', 'processing', 'completed', 'failed');
create type public.ingestion_source as enum (
    'cv_upload', 'conversation', 'employer_offer', 'ministry_market', 'training_catalog'
);
create type public.embedding_entity as enum ('candidate', 'job_offer', 'skill', 'occupation', 'training_course');

-- ---------------------------------------------------------------------------
-- Reference data
-- ---------------------------------------------------------------------------

create table public.governorates (
    code varchar(8) primary key,
    name_fr varchar(80) not null,
    name_ar varchar(80) not null
);

create table public.sectors (
    id uuid primary key default gen_random_uuid(),
    code varchar(32) not null unique,
    name_fr varchar(160) not null,
    name_ar varchar(160),
    parent_id uuid references public.sectors (id)
);

-- ---------------------------------------------------------------------------
-- Accounts
-- ---------------------------------------------------------------------------

create table public.users (
    id uuid primary key default gen_random_uuid(),
    role public.user_role not null,
    email varchar(320) unique,
    phone varchar(20) unique,
    password_hash varchar(255),
    preferred_language varchar(8) not null default 'ar-TN',
    is_active boolean not null default true,
    last_login_at timestamptz,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint users_contact_required check (email is not null or phone is not null)
);

-- ---------------------------------------------------------------------------
-- Skills taxonomy & occupations
-- ---------------------------------------------------------------------------

create table public.skill_categories (
    id uuid primary key default gen_random_uuid(),
    code varchar(32) not null unique,
    name_fr varchar(160) not null,
    name_ar varchar(160),
    parent_id uuid references public.skill_categories (id)
);

create table public.skills (
    id uuid primary key default gen_random_uuid(),
    code varchar(32) not null unique,
    label_fr varchar(200) not null,
    label_ar varchar(200),
    label_derja varchar(200),
    alt_labels jsonb not null default '[]',
    description text,
    skill_type public.skill_type not null,
    category_id uuid references public.skill_categories (id),
    status public.taxonomy_status not null default 'draft',
    esco_uri varchar(255),
    version integer not null default 1,
    validated_by uuid references public.users (id),
    validated_at timestamptz,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table public.skill_relations (
    source_skill_id uuid not null references public.skills (id) on delete cascade,
    target_skill_id uuid not null references public.skills (id) on delete cascade,
    relation_type public.skill_relation_type not null,
    primary key (source_skill_id, target_skill_id, relation_type),
    constraint skill_relations_no_self_ref check (source_skill_id <> target_skill_id)
);

create table public.skill_suggestions (
    id uuid primary key default gen_random_uuid(),
    proposed_label varchar(200) not null,
    normalized_label varchar(200) not null unique,
    skill_type public.skill_type,
    source public.ingestion_source not null,
    occurrences integer not null default 1,
    status public.suggestion_status not null default 'pending',
    resolved_skill_id uuid references public.skills (id),
    reviewed_by uuid references public.users (id),
    reviewed_at timestamptz,
    created_at timestamptz not null default now()
);

create table public.occupations (
    id uuid primary key default gen_random_uuid(),
    code varchar(32) not null unique,
    isco_code varchar(8),
    title_fr varchar(200) not null,
    title_ar varchar(200),
    alt_titles jsonb not null default '[]',
    description text,
    sector_id uuid references public.sectors (id),
    status public.taxonomy_status not null default 'draft',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table public.occupation_skills (
    occupation_id uuid not null references public.occupations (id) on delete cascade,
    skill_id uuid not null references public.skills (id) on delete cascade,
    requirement public.requirement_level not null,
    primary key (occupation_id, skill_id)
);

-- ---------------------------------------------------------------------------
-- Candidates (profile is PII-free; identity lives in candidate_pii)
-- ---------------------------------------------------------------------------

create table public.candidates (
    id uuid primary key default gen_random_uuid(),
    user_id uuid unique references public.users (id),
    onboarding_path public.onboarding_path not null,
    literacy_level public.literacy_level not null,
    governorate_code varchar(8) references public.governorates (code),
    delegation varchar(80),
    mobility_radius_km smallint,
    mobility_governorates jsonb not null default '[]',
    education_level public.education_level,
    years_experience numeric(4, 1),
    languages jsonb not null default '[]',
    available_from date,
    summary text,
    service_offer text,
    profile_completeness smallint not null default 0,
    profile_version integer not null default 1,
    raw_profile jsonb,
    consent_version varchar(16),
    consent_given_at timestamptz,
    deleted_at timestamptz,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint candidates_completeness_range check (profile_completeness between 0 and 100),
    constraint candidates_years_experience_positive check (years_experience >= 0)
);

create table public.candidate_pii (
    candidate_id uuid primary key references public.candidates (id) on delete cascade,
    full_name varchar(200),
    email varchar(320),
    phone varchar(20),
    date_of_birth date,
    gender varchar(16),
    address text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table public.candidate_skills (
    candidate_id uuid not null references public.candidates (id) on delete cascade,
    skill_id uuid not null references public.skills (id),
    level smallint not null,
    source public.skill_source not null,
    confidence numeric(3, 2) not null default 1.00,
    evidence text,
    primary key (candidate_id, skill_id),
    constraint candidate_skills_level_range check (level between 1 and 4),
    constraint candidate_skills_confidence_range check (confidence between 0 and 1)
);

create index candidate_skills_skill_idx on public.candidate_skills (skill_id);

create table public.candidate_experiences (
    id uuid primary key default gen_random_uuid(),
    candidate_id uuid not null references public.candidates (id) on delete cascade,
    occupation_id uuid references public.occupations (id),
    job_title_raw varchar(200) not null,
    employer_name varchar(200),
    is_informal boolean not null default false,
    start_date date,
    end_date date,
    duration_months smallint,
    governorate_code varchar(8) references public.governorates (code),
    description text
);

create index candidate_experiences_candidate_idx on public.candidate_experiences (candidate_id);

create table public.candidate_educations (
    id uuid primary key default gen_random_uuid(),
    candidate_id uuid not null references public.candidates (id) on delete cascade,
    level public.education_level not null,
    field_of_study varchar(200),
    institution varchar(200),
    graduation_year smallint,
    country_code varchar(2) not null default 'TN'
);

create index candidate_educations_candidate_idx on public.candidate_educations (candidate_id);

create table public.candidate_desired_occupations (
    candidate_id uuid not null references public.candidates (id) on delete cascade,
    occupation_id uuid not null references public.occupations (id),
    priority smallint not null default 1,
    primary key (candidate_id, occupation_id)
);

create table public.conversation_sessions (
    id uuid primary key default gen_random_uuid(),
    candidate_id uuid references public.candidates (id) on delete cascade,
    channel public.conversation_channel not null,
    onboarding_path public.onboarding_path not null,
    language varchar(8) not null default 'ar-TN',
    status public.processing_status not null default 'pending',
    transcript jsonb not null default '[]',
    detected_intents jsonb not null default '[]',
    appetence jsonb not null default '{}',
    started_at timestamptz not null default now(),
    ended_at timestamptz
);

create index conversation_sessions_candidate_idx on public.conversation_sessions (candidate_id);

-- ---------------------------------------------------------------------------
-- Platform: raw documents & ingestion runs
-- ---------------------------------------------------------------------------

create table public.documents (
    id uuid primary key default gen_random_uuid(),
    doc_type public.document_type not null,
    owner_user_id uuid references public.users (id),
    candidate_id uuid references public.candidates (id) on delete cascade,
    storage_path varchar(512) not null,
    mime_type varchar(100) not null,
    size_bytes bigint not null,
    sha256 varchar(64) not null,
    processing_status public.processing_status not null default 'pending',
    pii_redacted boolean not null default false,
    redacted_text text,
    extraction jsonb,
    error text,
    processed_at timestamptz,
    created_at timestamptz not null default now()
);

create index documents_candidate_idx on public.documents (candidate_id);
create index documents_sha256_idx on public.documents (sha256);

create table public.ingestion_jobs (
    id uuid primary key default gen_random_uuid(),
    source public.ingestion_source not null,
    status public.processing_status not null default 'pending',
    document_id uuid references public.documents (id),
    triggered_by uuid references public.users (id),
    pipeline_version varchar(32) not null,
    records_total integer not null default 0,
    records_ok integer not null default 0,
    records_failed integer not null default 0,
    errors jsonb not null default '[]',
    started_at timestamptz,
    finished_at timestamptz,
    created_at timestamptz not null default now()
);

-- ---------------------------------------------------------------------------
-- Employers (WP4 table, extended), offers, applications, feedback
-- ---------------------------------------------------------------------------

create table if not exists public.employers (
    id uuid primary key default gen_random_uuid(),
    company_name text not null,
    email text not null unique,
    password_hash text not null,
    sector text not null,
    company_size public.company_size not null,
    created_at timestamptz not null default now(),
    verified boolean not null default false
);

create index if not exists employers_email_idx on public.employers (email);

alter table public.employers add column if not exists user_id uuid unique references public.users (id);
alter table public.employers add column if not exists sector_id uuid references public.sectors (id);
alter table public.employers add column if not exists tax_id varchar(32) unique;
alter table public.employers add column if not exists governorate_code varchar(8) references public.governorates (code);
alter table public.employers add column if not exists website varchar(255);
alter table public.employers add column if not exists description text;
alter table public.employers add column if not exists updated_at timestamptz not null default now();

create table public.job_offers (
    id uuid primary key default gen_random_uuid(),
    employer_id uuid references public.employers (id) on delete cascade,
    title varchar(200) not null,
    description_raw text not null,
    description_normalized text,
    occupation_id uuid references public.occupations (id),
    sector_id uuid references public.sectors (id),
    contract_type public.contract_type not null,
    work_mode public.work_mode not null default 'on_site',
    governorate_code varchar(8) not null references public.governorates (code),
    delegation varchar(80),
    positions_count smallint not null default 1,
    min_years_experience numeric(4, 1) not null default 0,
    education_level_min public.education_level,
    salary_min_tnd numeric(10, 2),
    salary_max_tnd numeric(10, 2),
    languages_required jsonb not null default '[]',
    status public.offer_status not null default 'draft',
    source public.offer_source not null default 'employer_form',
    external_ref varchar(64),
    guardrail_flags jsonb not null default '[]',
    published_at timestamptz,
    expires_at timestamptz,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint job_offers_positions_positive check (positions_count >= 1),
    constraint job_offers_salary_range check (
        salary_min_tnd is null or salary_max_tnd is null or salary_min_tnd <= salary_max_tnd
    )
);

create index job_offers_employer_idx on public.job_offers (employer_id);
create index job_offers_status_governorate_idx on public.job_offers (status, governorate_code);

create table public.job_offer_skills (
    job_offer_id uuid not null references public.job_offers (id) on delete cascade,
    skill_id uuid not null references public.skills (id),
    requirement public.requirement_level not null,
    min_level smallint not null default 1,
    primary key (job_offer_id, skill_id),
    constraint job_offer_skills_level_range check (min_level between 1 and 4)
);

create index job_offer_skills_skill_idx on public.job_offer_skills (skill_id);

-- ---------------------------------------------------------------------------
-- Matching (written by WP3)
-- ---------------------------------------------------------------------------

create table public.match_results (
    id uuid primary key default gen_random_uuid(),
    candidate_id uuid not null references public.candidates (id) on delete cascade,
    job_offer_id uuid not null references public.job_offers (id) on delete cascade,
    score_global numeric(5, 2) not null,
    score_hard_skills numeric(5, 2) not null,
    score_experience numeric(5, 2) not null,
    score_soft_skills numeric(5, 2) not null,
    score_location numeric(5, 2) not null,
    weights jsonb not null,
    model_version varchar(32) not null,
    is_current boolean not null default true,
    computed_at timestamptz not null default now(),
    constraint match_results_score_global_range check (score_global between 0 and 100),
    constraint match_results_score_hard_skills_range check (score_hard_skills between 0 and 100),
    constraint match_results_score_experience_range check (score_experience between 0 and 100),
    constraint match_results_score_soft_skills_range check (score_soft_skills between 0 and 100),
    constraint match_results_score_location_range check (score_location between 0 and 100),
    constraint match_results_pair_version_key unique (candidate_id, job_offer_id, model_version)
);

create index match_results_candidate_score_idx on public.match_results (candidate_id, score_global desc);
create index match_results_offer_score_idx on public.match_results (job_offer_id, score_global desc);

create table public.skill_gaps (
    id uuid primary key default gen_random_uuid(),
    match_result_id uuid not null references public.match_results (id) on delete cascade,
    skill_id uuid not null references public.skills (id),
    gap_type public.gap_type not null,
    requirement public.requirement_level not null,
    required_level smallint not null,
    current_level smallint,
    constraint skill_gaps_match_skill_key unique (match_result_id, skill_id)
);

create table public.applications (
    id uuid primary key default gen_random_uuid(),
    candidate_id uuid not null references public.candidates (id) on delete cascade,
    job_offer_id uuid not null references public.job_offers (id) on delete cascade,
    match_result_id uuid references public.match_results (id),
    status public.application_status not null default 'submitted',
    cover_note text,
    applied_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint applications_candidate_offer_key unique (candidate_id, job_offer_id)
);

create index applications_candidate_idx on public.applications (candidate_id);
create index applications_job_offer_idx on public.applications (job_offer_id);

create table public.hiring_feedback (
    id uuid primary key default gen_random_uuid(),
    application_id uuid not null references public.applications (id) on delete cascade,
    employer_id uuid not null references public.employers (id),
    decision public.hiring_decision not null,
    reason_code varchar(64),
    match_quality smallint,
    comment text,
    created_at timestamptz not null default now(),
    constraint hiring_feedback_quality_range check (match_quality between 1 and 5)
);

create index hiring_feedback_application_idx on public.hiring_feedback (application_id);

-- ---------------------------------------------------------------------------
-- Training catalog, certifications & roadmaps
-- ---------------------------------------------------------------------------

create table public.training_providers (
    id uuid primary key default gen_random_uuid(),
    name varchar(200) not null,
    provider_type varchar(32) not null,
    accreditation_ref varchar(64),
    governorate_code varchar(8) references public.governorates (code),
    website varchar(255),
    user_id uuid references public.users (id),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table public.training_courses (
    id uuid primary key default gen_random_uuid(),
    provider_id uuid not null references public.training_providers (id) on delete cascade,
    title varchar(200) not null,
    description text,
    modality public.course_modality not null,
    duration_hours smallint,
    cost_tnd numeric(10, 2),
    governorate_code varchar(8) references public.governorates (code),
    language varchar(8) not null default 'fr',
    certification_name varchar(200),
    external_ref varchar(64),
    is_active boolean not null default true,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index training_courses_provider_idx on public.training_courses (provider_id);

create table public.training_course_skills (
    training_course_id uuid not null references public.training_courses (id) on delete cascade,
    skill_id uuid not null references public.skills (id),
    target_level smallint not null,
    primary key (training_course_id, skill_id),
    constraint training_course_skills_level_range check (target_level between 1 and 4)
);

create index training_course_skills_skill_idx on public.training_course_skills (skill_id);

create table public.candidate_certifications (
    id uuid primary key default gen_random_uuid(),
    candidate_id uuid not null references public.candidates (id) on delete cascade,
    training_course_id uuid references public.training_courses (id),
    provider_id uuid references public.training_providers (id),
    title varchar(200) not null,
    issued_on date,
    expires_on date,
    verification_status public.verification_status not null default 'pending',
    document_id uuid references public.documents (id),
    created_at timestamptz not null default now()
);

create index candidate_certifications_candidate_idx on public.candidate_certifications (candidate_id);

create table public.roadmaps (
    id uuid primary key default gen_random_uuid(),
    candidate_id uuid not null references public.candidates (id) on delete cascade,
    target_job_offer_id uuid references public.job_offers (id) on delete set null,
    target_occupation_id uuid references public.occupations (id),
    status public.roadmap_status not null default 'active',
    progress_pct smallint not null default 0,
    model_version varchar(32) not null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint roadmaps_target_required check (target_job_offer_id is not null or target_occupation_id is not null),
    constraint roadmaps_progress_range check (progress_pct between 0 and 100)
);

create index roadmaps_candidate_idx on public.roadmaps (candidate_id);

create table public.roadmap_items (
    id uuid primary key default gen_random_uuid(),
    roadmap_id uuid not null references public.roadmaps (id) on delete cascade,
    skill_id uuid not null references public.skills (id),
    training_course_id uuid references public.training_courses (id) on delete set null,
    position smallint not null,
    status public.roadmap_item_status not null default 'todo',
    started_at timestamptz,
    completed_at timestamptz,
    constraint roadmap_items_position_key unique (roadmap_id, position)
);

-- ---------------------------------------------------------------------------
-- Ministry market data
-- ---------------------------------------------------------------------------

create table public.market_datasets (
    id uuid primary key default gen_random_uuid(),
    title varchar(200) not null,
    origin public.market_data_origin not null,
    publisher varchar(200) not null,
    period_start date not null,
    period_end date not null,
    document_id uuid references public.documents (id),
    ingestion_job_id uuid references public.ingestion_jobs (id),
    uploaded_by uuid references public.users (id),
    created_at timestamptz not null default now(),
    constraint market_datasets_period_order check (period_start <= period_end)
);

create table public.market_indicators (
    id uuid primary key default gen_random_uuid(),
    dataset_id uuid not null references public.market_datasets (id) on delete cascade,
    indicator_type public.market_indicator_type not null,
    occupation_id uuid references public.occupations (id),
    skill_id uuid references public.skills (id),
    sector_id uuid references public.sectors (id),
    governorate_code varchar(8) references public.governorates (code),
    period_start date not null,
    period_end date not null,
    value numeric(14, 4) not null,
    unit varchar(16) not null,
    extra jsonb not null default '{}'
);

create index market_indicators_dataset_idx on public.market_indicators (dataset_id);
create index market_indicators_lookup_idx on public.market_indicators (indicator_type, governorate_code, period_start);

-- ---------------------------------------------------------------------------
-- Vector store (pgvector) & audit log
-- ---------------------------------------------------------------------------

create table public.embeddings (
    id uuid primary key default gen_random_uuid(),
    entity_type public.embedding_entity not null,
    entity_id uuid not null,
    model_name varchar(128) not null,
    embedding vector(768) not null,
    content_hash varchar(64) not null,
    created_at timestamptz not null default now(),
    constraint embeddings_entity_model_key unique (entity_type, entity_id, model_name)
);

create index embeddings_hnsw_idx on public.embeddings using hnsw (embedding vector_cosine_ops);

create table public.audit_logs (
    id bigint generated always as identity primary key,
    actor_user_id uuid references public.users (id),
    actor_service varchar(32),
    action varchar(64) not null,
    entity_type varchar(64) not null,
    entity_id varchar(64),
    payload jsonb not null default '{}',
    created_at timestamptz not null default now()
);

create index audit_logs_entity_idx on public.audit_logs (entity_type, entity_id);

-- ---------------------------------------------------------------------------
-- updated_at maintenance
-- ---------------------------------------------------------------------------

create or replace function public.set_updated_at() returns trigger
language plpgsql as $$
begin
    new.updated_at = now();
    return new;
end
$$;

do $$
declare
    tbl text;
begin
    foreach tbl in array array[
        'users', 'skills', 'occupations', 'candidates', 'candidate_pii', 'employers', 'job_offers',
        'applications', 'training_providers', 'training_courses', 'roadmaps'
    ] loop
        execute format(
            'create trigger %I before update on public.%I for each row execute function public.set_updated_at()',
            tbl || '_set_updated_at', tbl
        );
    end loop;
end
$$;

-- ---------------------------------------------------------------------------
-- Row Level Security: deny-by-default through the Supabase REST API.
-- Module backends connect with the service role / table owner, which bypasses RLS.
-- ---------------------------------------------------------------------------

do $$
declare
    tbl text;
begin
    foreach tbl in array array[
        'governorates', 'sectors', 'users', 'skill_categories', 'skills', 'skill_relations',
        'skill_suggestions', 'occupations', 'occupation_skills', 'candidates', 'candidate_pii',
        'candidate_skills', 'candidate_experiences', 'candidate_educations',
        'candidate_desired_occupations', 'conversation_sessions', 'documents', 'ingestion_jobs',
        'employers', 'job_offers', 'job_offer_skills', 'match_results', 'skill_gaps', 'applications',
        'hiring_feedback', 'training_providers', 'training_courses', 'training_course_skills',
        'candidate_certifications', 'roadmaps', 'roadmap_items', 'market_datasets',
        'market_indicators', 'embeddings', 'audit_logs'
    ] loop
        execute format('alter table public.%I enable row level security', tbl);
    end loop;
end
$$;

-- ---------------------------------------------------------------------------
-- Seed: the 24 governorates (ISO 3166-2:TN)
-- ---------------------------------------------------------------------------

insert into public.governorates (code, name_fr, name_ar) values
    ('TN-11', 'Tunis', 'تونس'),
    ('TN-12', 'Ariana', 'أريانة'),
    ('TN-13', 'Ben Arous', 'بن عروس'),
    ('TN-14', 'Manouba', 'منوبة'),
    ('TN-21', 'Nabeul', 'نابل'),
    ('TN-22', 'Zaghouan', 'زغوان'),
    ('TN-23', 'Bizerte', 'بنزرت'),
    ('TN-31', 'Béja', 'باجة'),
    ('TN-32', 'Jendouba', 'جندوبة'),
    ('TN-33', 'Le Kef', 'الكاف'),
    ('TN-34', 'Siliana', 'سليانة'),
    ('TN-41', 'Kairouan', 'القيروان'),
    ('TN-42', 'Kasserine', 'القصرين'),
    ('TN-43', 'Sidi Bouzid', 'سيدي بوزيد'),
    ('TN-51', 'Sousse', 'سوسة'),
    ('TN-52', 'Monastir', 'المنستير'),
    ('TN-53', 'Mahdia', 'المهدية'),
    ('TN-61', 'Sfax', 'صفاقس'),
    ('TN-71', 'Gafsa', 'قفصة'),
    ('TN-72', 'Tozeur', 'توزر'),
    ('TN-73', 'Kébili', 'قبلي'),
    ('TN-81', 'Gabès', 'قابس'),
    ('TN-82', 'Médenine', 'مدنين'),
    ('TN-83', 'Tataouine', 'تطاوين');
