-- Server-side sessions — only present when token_strategy=session.
CREATE TABLE app_session (
    token      TEXT PRIMARY KEY,
    user_id    TEXT NOT NULL,
    expires_at TIMESTAMP NOT NULL
);
