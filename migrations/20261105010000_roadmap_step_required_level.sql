ALTER TABLE roadmap_items
    ADD COLUMN required_level SMALLINT NOT NULL DEFAULT 2;

ALTER TABLE roadmap_items
    ADD CONSTRAINT roadmap_items_required_level_range
    CHECK (required_level BETWEEN 1 AND 4);

CREATE INDEX job_offers_occupation_published_idx
    ON job_offers (occupation_id, published_at);
