# Cibus Home Assignment

## What This Service Does

A FastAPI-based message board API with:
- user registration and login
- JWT-based authentication
- posting, listing, voting, and deleting messages
- database migrations on startup that set required tables and indexes in the database

## Prerequisites

For standalone (non-Docker) run:
- Python 3.10
- PostgreSQL 18.3 running and reachable
- dependencies installed from `requirements.txt`
- `.env` file present in the project root directory (already included in this project)

For Docker Compose run:
- Docker Engine + Docker Compose
- `.env` file present in the project root directory (already included in this project)

## `.env` File

The project already includes an `.env` file with initial development settings.

- Docker Compose mode: works out of the box with this file.
- Standalone mode: partially ready, but you still need a matching local PostgreSQL setup (database/user/password).

The app reads configuration from `.env`:

Main variables:
- `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USERNAME`, `DB_PASSWORD`
- `JWT_SECRET`
- `SERVER_HOST`, `SERVER_PORT`
- optional for Docker host mapping: `DB_EXTERNAL_PORT`

Note: `.env` in this repository is for development/home-assignment usage only.

## Run Server Without Docker

1. Create/activate a Python 3.10 environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. In local PostgreSQL 18.3, create the database, user, and password to match `.env` values (`DB_NAME`, `DB_USERNAME`, `DB_PASSWORD`).
4. Make sure PostgreSQL is up and that `.env` points to it.
5. Start server:

```bash
python3 main.py
```

6. Access API:
- `http://localhost:<SERVER_PORT>/docs`
- default: `http://localhost:9000/docs`

## Run Server With Docker Compose

This option brings:
- API container (`cibus_api`)
- PostgreSQL 18.3 container (`cibus_db`)
- isolated network between them
- persistent DB volume (`postgres_data`)
- health checks and startup ordering

Start:

```bash
docker compose up --build
```

Detached mode:

```bash
docker compose up -d --build
```

Stop:

```bash
docker compose down
```

Stop and remove DB volume:

```bash
docker compose down -v
```

Useful:

```bash
docker compose ps
docker compose logs -f api
docker compose logs -f db
```

## Tests

### 1) Unit + Component tests (pytest)

Run all pytest tests:

```bash
python3 tests/run_pytests.py
```

Run only unit tests:

```bash
python3 tests/run_pytests.py tests/unit
```

Run only component tests:

```bash
python3 tests/run_pytests.py tests/component
```

### 2) System tests (Postman collection)

Prerequisites:
- server is up and running
- collection file: `tests/system/CibusHomeAssignment.postman_collection.json`
- execution option: Postman Desktop app (import and run collection manually)
- execution option: Postman CLI (`postman`)
- execution option: Newman CLI (`newman`)

Run:

```bash
bash tests/run_system_tests.sh
```

What this script does:
- prints execution metadata and report filenames
- starts `main.py` locally
- waits for server readiness (`/openapi.json`)
- optionally runs DB cleanup SQL (`tests/system/pre_test_cleanup.sql`) if `psql` and DB env vars are available
- runs Postman collection via `newman` (or `postman` CLI fallback)
- writes reports to `tests/system/reports`
- stops the server process on exit

Run via Postman Desktop app:
1. Open Postman.
2. Import `tests/system/CibusHomeAssignment.postman_collection.json`.
3. Ensure the API server is running.
4. Run the collection from Collection Runner.

Run via Postman/Newman CLI manually (server must already be running):

```bash
postman collection run tests/system/CibusHomeAssignment.postman_collection.json -r cli
```

```bash
newman run tests/system/CibusHomeAssignment.postman_collection.json --reporters cli
```

## Server Bootstrap and Shutdown

Implemented in the FastAPI lifespan (`main.py`):

On startup:
- loads settings
- creates PostgreSQL client (`PSClient`)
- runs migrations (`migrate()`)
- stores JWT secret on app state

On shutdown:
- closes PostgreSQL client pool

## Database Schema and Migrations

Migration files are located under `migrations/` and are executed on server startup (`migrate()` in `main.py`).

Note: in standalone mode (no Docker), the database and DB user/password must already exist before starting the server, aligned with the `.env` file values.

Migration flow:
- migration history is tracked in `schema_migrations` (`version`, `applied_at`)
- migration files are read in lexicographical order (`*.sql`)
- already-applied files are skipped
- each migration runs in a DB transaction

Migration files:
- `001_init.sql`
- `002_add_vote_count_to_messages.sql`
- `003_uq_author_message_hash.sql`

Current schema overview:
- `users`: user identity and password hash
- `messages`: authored message content, soft-delete timestamp, vote count
- `message_votes`: one vote per (`user_id`, `message_id`) with values `-1` or `1`
- `schema_migrations`: applied migration versions

## Implementation Decisions

- There is only one MessageBoard in the system.
- Voting is allowed only on messages that were not deleted.
- A user can vote for their own messages.
- A user can vote more than once for the same message and will not be replied with error. ONLY THE LATEST vote is counted in the message vote count and registered.
- A user cannot post a new message if the same user already has a non-deleted message with the exact same content.
- Deleting an already deleted message does not return an error. Since there is no additional state change, the API returns the same `204` response as it does for a first successful deletion.
- Message retrieval (`GET /messages` and `GET /user/messages`) supports pagination via the `next_result` query parameter.
- There is a hard maximum page size of `50` items per page (enforced in `repositories/message_repo.py`).
- Logout behavior:
  - logout is implemented as a stateless JWT logout
  - server returns `204 No Content` and does not revoke JWT server-side
  - client is expected to remove/discard the token locally
  - stronger alternatives exist (token revocation lists, refresh-token architecture with an additional refresh endpoint, Redis-backed revocation), but were intentionally not implemented for this assignment to keep the solution simple and stateless

## API Endpoints (Short Overview)

- `POST /register`  
  Creates a new user.

- `POST /login`  
  Validates credentials and returns JWT access token.

- `POST /logout`  
  Stateless logout response (`204`); client is expected to discard token.

- `GET /messages`  
  Lists messages with pagination (`limit`, `next_result`), requires auth.

- `POST /messages`  
  Creates a new message for authenticated user.

- `POST /messages/{message_id}/vote`  
  Votes up/down on a message.

- `DELETE /messages/{message_id}`  
  Deletes a message (owner/permission rules enforced in service layer).

- `GET /user/messages`  
  Lists messages created by current authenticated user.

- `GET /docs`  
  Swagger UI for interactive API exploration.
