-- Sample table for the `example` vertical slice. Real migrations replace/extend it.
-- contracts/db/migrations/** is a server-owned contract (source of truth for jOOQ codegen).
CREATE TABLE example (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    label       TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
