-- Deletes only entities created by this Postman suite.
-- Marker users are prefixed with:
--   pm_req_author_
--   pm_req_voter_

BEGIN;

WITH test_users AS (
    SELECT id
    FROM users
    WHERE username LIKE 'pm_req_author_%'
       OR username LIKE 'pm_req_voter_%'
),
test_messages AS (
    SELECT id
    FROM messages
    WHERE author_id IN (SELECT id FROM test_users)
)
DELETE FROM message_votes
WHERE user_id IN (SELECT id FROM test_users)
   OR message_id IN (SELECT id FROM test_messages);

DELETE FROM messages
WHERE author_id IN (
    SELECT id
    FROM users
    WHERE username LIKE 'pm_req_author_%'
       OR username LIKE 'pm_req_voter_%'
);

DELETE FROM users
WHERE username LIKE 'pm_req_author_%'
   OR username LIKE 'pm_req_voter_%';

COMMIT;
