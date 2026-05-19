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
