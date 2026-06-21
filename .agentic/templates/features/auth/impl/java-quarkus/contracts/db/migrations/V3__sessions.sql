-- Server-side sessions — only when token_strategy=session.
CREATE TABLE app_session (
    token      TEXT PRIMARY KEY,
    user_id    UUID NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
    expires_at TIMESTAMPTZ NOT NULL
);
