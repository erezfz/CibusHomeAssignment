CREATE EXTENSION IF NOT EXISTS "pgcrypto";


CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    author_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    content TEXT NOT NULL,

    deleted_at TIMESTAMPTZ NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


CREATE TABLE IF NOT EXISTS message_votes (
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    message_id UUID NOT NULL REFERENCES messages(id),

    vote SMALLINT NOT NULL CHECK (vote IN (-1, 1)),

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    PRIMARY KEY (user_id, message_id)
);


CREATE INDEX IF NOT EXISTS idx_messages_author_id
ON messages(author_id);

CREATE INDEX IF NOT EXISTS idx_messages_created_at_id
ON messages(created_at DESC, id DESC);

CREATE INDEX IF NOT EXISTS idx_message_votes_message_id
ON message_votes(message_id);


CREATE INDEX IF NOT EXISTS idx_message_votes_user_id
ON message_votes(user_id);