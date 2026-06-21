-- Sample table for the `example` vertical slice. Real migrations replace/extend it.
-- contracts/db/migrations/** is a server-owned contract. Portable types (test = SQLite).
-- Production (Postgres): id UUID, created_at TIMESTAMPTZ.
CREATE TABLE example (
    id          TEXT PRIMARY KEY,
    label       TEXT NOT NULL,
    created_at  TIMESTAMP NOT NULL
);
