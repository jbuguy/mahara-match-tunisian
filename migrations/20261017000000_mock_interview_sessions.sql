CREATE TABLE IF NOT EXISTS mock_interview_sessions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    candidate_id uuid NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
    target_title varchar(200) NOT NULL,
    occupation_code varchar(32) REFERENCES occupations(code),
    target_offer_id uuid REFERENCES job_offers(id) ON DELETE SET NULL,
    language varchar(16) NOT NULL CHECK (language IN ('fr', 'ar', 'derja')),
    question_count smallint NOT NULL CHECK (question_count IN (3, 5, 8)),
    questions jsonb NOT NULL DEFAULT '[]'::jsonb,
    answers jsonb NOT NULL DEFAULT '[]'::jsonb,
    draft_answer text,
    feedback jsonb,
    status varchar(16) NOT NULL DEFAULT 'in_progress' CHECK (status IN ('in_progress', 'completed')),
    saved boolean NOT NULL DEFAULT false,
    consented_at timestamptz NOT NULL,
    expires_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_mock_interview_sessions_candidate_id ON mock_interview_sessions(candidate_id);
CREATE INDEX IF NOT EXISTS ix_mock_interview_sessions_expires_at ON mock_interview_sessions(expires_at);
ALTER TABLE mock_interview_sessions ENABLE ROW LEVEL SECURITY;
