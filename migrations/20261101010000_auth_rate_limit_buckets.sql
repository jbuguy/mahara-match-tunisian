CREATE TABLE IF NOT EXISTS auth_rate_limit_buckets (
    bucket_key varchar(64) NOT NULL,
    window_start timestamptz NOT NULL,
    request_count integer NOT NULL CHECK (request_count >= 1),
    PRIMARY KEY (bucket_key, window_start)
);

CREATE INDEX IF NOT EXISTS ix_auth_rate_limit_buckets_window_start
    ON auth_rate_limit_buckets (window_start);

ALTER TABLE auth_rate_limit_buckets ENABLE ROW LEVEL SECURITY;
