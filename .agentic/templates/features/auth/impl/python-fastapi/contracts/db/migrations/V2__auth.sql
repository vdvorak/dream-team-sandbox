-- Auth: user accounts. id UUID (TEXT for the SQLite test), email unique, bcrypt password_hash.
-- Production (Postgres): id UUID, created_at TIMESTAMPTZ.
CREATE TABLE app_user (
    id            TEXT PRIMARY KEY,
    email         TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL DEFAULT 'user',
    created_at    TIMESTAMP NOT NULL
);
