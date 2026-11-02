ALTER TABLE users
    ADD COLUMN deletion_requested_at timestamptz;

CREATE INDEX ix_candidates_deleted_at
    ON candidates (deleted_at)
    WHERE deleted_at IS NOT NULL;
