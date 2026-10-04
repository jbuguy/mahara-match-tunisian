-- Mahara WP6 Employee Module: PostgreSQL schema.
-- HISTORICAL ONLY: WP1 root migrations are the sole shared schema source of truth.
-- Do not apply this file to the shared Supabase database.

create extension if not exists pgcrypto;

-- ---------------------------------------------------------------------------
-- Reference data
-- ---------------------------------------------------------------------------

create table if not exists governorates (
    code    text primary key,
    name_fr text not null,
    name_ar text not null
);

create table if not exists skills (
    id         uuid primary key default gen_random_uuid(),
    code       text not null unique,
    label_fr   text not null,
    alt_labels jsonb not null default '[]'::jsonb,
    skill_type text not null check (skill_type in ('hard', 'soft', 'language')),
    status     text check (status in ('draft', 'validated', 'deprecated'))
);

create table if not exists occupations (
    id       uuid primary key default gen_random_uuid(),
    code     text not null unique,
    title_fr text not null
);

-- ---------------------------------------------------------------------------
-- Users and candidates
-- ---------------------------------------------------------------------------

create table if not exists users (
    id                 uuid primary key default gen_random_uuid(),
    email              text not null unique,
    role               text not null default 'candidate'
                       check (role in ('candidate', 'employer', 'admin', 'ministry', 'training_provider')),
    preferred_language text not null default 'fr',
    last_login_at      timestamptz
);

create table if not exists candidates (
    id               uuid primary key default gen_random_uuid(),
    user_id          uuid not null unique references users (id) on delete cascade,
    onboarding_path  text not null check (onboarding_path in ('cv_upload', 'derja_detailed')),
    literacy_level   text not null default 'literate'
                     check (literacy_level in ('literate', 'basic', 'non_literate')),
    governorate_code text references governorates (code),
    education_level  text check (education_level in (
                         'none', 'primary', 'lower_secondary', 'baccalaureate',
                         'vocational_cap', 'vocational_btp', 'vocational_bts',
                         'licence', 'master', 'engineer', 'doctorate')),
    years_experience integer check (years_experience >= 0),
    languages        jsonb not null default '[]'::jsonb,   -- [{code, level}]
    summary          text,
    available_from   date,
    consent_version  text,
    consent_given_at timestamptz
);

-- Identity kept apart from the profile.
create table if not exists candidate_pii (
    candidate_id uuid primary key references candidates (id) on delete cascade,
    full_name    text,
    email        text,
    phone        text,
    photo        bytea  -- the candidate's own photo (256x256 JPEG); null = use the Google photo
);

create table if not exists candidate_skills (
    candidate_id uuid not null references candidates (id) on delete cascade,
    skill_id     uuid not null references skills (id),
    level        smallint not null check (level between 1 and 4),
    source       text not null check (source in ('self_declared', 'cv')),
    confidence   real,
    primary key (candidate_id, skill_id)
);

create table if not exists candidate_experiences (
    id              uuid primary key default gen_random_uuid(),
    candidate_id    uuid not null references candidates (id) on delete cascade,
    job_title_raw   text not null,
    employer_name   text,
    start_date      date,
    end_date        date,
    duration_months integer check (duration_months >= 0),
    description     text
);

create table if not exists candidate_educations (
    id              uuid primary key default gen_random_uuid(),
    candidate_id    uuid not null references candidates (id) on delete cascade,
    level           text check (level in (
                        'none', 'primary', 'lower_secondary', 'baccalaureate',
                        'vocational_cap', 'vocational_btp', 'vocational_bts',
                        'licence', 'master', 'engineer', 'doctorate')),
    field_of_study  text,
    institution     text,
    graduation_year integer
);

create table if not exists candidate_desired_occupations (
    candidate_id  uuid not null references candidates (id) on delete cascade,
    occupation_id uuid not null references occupations (id),
    priority      smallint,
    primary key (candidate_id, occupation_id)
);

-- Checks added after the first release: re-created here so databases made by an
-- older version of this file get them too ("create table if not exists" skips them).
alter table users  drop constraint if exists users_role_check;
alter table users  add  constraint users_role_check
    check (role in ('candidate', 'employer', 'admin', 'ministry', 'training_provider'));
alter table skills drop constraint if exists skills_status_check;
alter table skills add  constraint skills_status_check
    check (status in ('draft', 'validated', 'deprecated'));

-- Columns added after the first release.
alter table candidate_pii add column if not exists photo bytea;

-- ---------------------------------------------------------------------------
-- Row level security: on everywhere, no policies (only the backend connects).
-- ---------------------------------------------------------------------------

alter table governorates                  enable row level security;
alter table skills                        enable row level security;
alter table occupations                   enable row level security;
alter table users                         enable row level security;
alter table candidates                    enable row level security;
alter table candidate_pii                 enable row level security;
alter table candidate_skills              enable row level security;
alter table candidate_experiences         enable row level security;
alter table candidate_educations          enable row level security;
alter table candidate_desired_occupations enable row level security;

-- ---------------------------------------------------------------------------
-- The 24 governorates
-- ---------------------------------------------------------------------------

insert into governorates (code, name_fr, name_ar) values
    ('TN-11', 'Tunis',       'تونس'),
    ('TN-12', 'Ariana',      'أريانة'),
    ('TN-13', 'Ben Arous',   'بن عروس'),
    ('TN-14', 'Manouba',     'منوبة'),
    ('TN-21', 'Nabeul',      'نابل'),
    ('TN-22', 'Zaghouan',    'زغوان'),
    ('TN-23', 'Bizerte',     'بنزرت'),
    ('TN-31', 'Béja',        'باجة'),
    ('TN-32', 'Jendouba',    'جندوبة'),
    ('TN-33', 'Le Kef',      'الكاف'),
    ('TN-34', 'Siliana',     'سليانة'),
    ('TN-41', 'Kairouan',    'القيروان'),
    ('TN-42', 'Kasserine',   'القصرين'),
    ('TN-43', 'Sidi Bouzid', 'سيدي بوزيد'),
    ('TN-51', 'Sousse',      'سوسة'),
    ('TN-52', 'Monastir',    'المنستير'),
    ('TN-53', 'Mahdia',      'المهدية'),
    ('TN-61', 'Sfax',        'صفاقس'),
    ('TN-71', 'Gafsa',       'قفصة'),
    ('TN-72', 'Tozeur',      'توزر'),
    ('TN-73', 'Kébili',      'قبلي'),
    ('TN-81', 'Gabès',       'قابس'),
    ('TN-82', 'Médenine',    'مدنين'),
    ('TN-83', 'Tataouine',   'تطاوين')
on conflict (code) do update
    set name_fr = excluded.name_fr,
        name_ar = excluded.name_ar;
