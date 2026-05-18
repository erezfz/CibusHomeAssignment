CREATE UNIQUE INDEX uq_author_message_hash
ON messages (
    author_id,
    digest(content, 'sha256')
)
WHERE deleted_at IS NULL;