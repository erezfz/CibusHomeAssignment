#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
SYSTEM_DIR="$ROOT_DIR/system"
COLLECTION_FILE="$SYSTEM_DIR/CibusHomeAssignment.postman_collection.json"
PRE_CLEAN_SQL="$SYSTEM_DIR/pre_test_cleanup.sql"
ENV_FILE="$ROOT_DIR/../.env"
REPORT_DIR="$SYSTEM_DIR/reports"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
REPORT_FILE="$REPORT_DIR/postman_run_${TIMESTAMP}.log"
APP_DIR="$ROOT_DIR/.."
SERVER_HOST="${SERVER_HOST:-localhost}"
SERVER_PORT="${SERVER_PORT:-9000}"
SERVER_URL="http://${SERVER_HOST}:${SERVER_PORT}"
SERVER_OPENAPI_URL="${SERVER_URL}/openapi.json"
SERVER_LOG_FILE="$REPORT_DIR/fastapi_server_${TIMESTAMP}.log"
SERVER_PID=""
EXECUTED_BY="$(id -un 2>/dev/null || whoami)"

mkdir -p "$REPORT_DIR"

echo "Running system tests..."
echo "Executed by: $EXECUTED_BY"
echo "Execution timestamp: $TIMESTAMP"
echo "Collection: $COLLECTION_FILE"
echo "Reports directory: $REPORT_DIR"
echo "Postman report file: $REPORT_FILE"
echo "FastAPI server log file: $SERVER_LOG_FILE"

if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

SERVER_HOST="${SERVER_HOST:-localhost}"
SERVER_PORT="${SERVER_PORT:-9000}"
SERVER_URL="http://${SERVER_HOST}:${SERVER_PORT}"
SERVER_OPENAPI_URL="${SERVER_URL}/openapi.json"

cleanup_server() {
  if [[ -n "$SERVER_PID" ]] && kill -0 "$SERVER_PID" >/dev/null 2>&1; then
    echo "Stopping FastAPI server (pid $SERVER_PID)..."
    kill -TERM "$SERVER_PID" >/dev/null 2>&1 || true
    for _ in $(seq 1 5); do
      if ! kill -0 "$SERVER_PID" >/dev/null 2>&1; then
        break
      fi
      sleep 1
    done
    if kill -0 "$SERVER_PID" >/dev/null 2>&1; then
      echo "FastAPI server did not stop on TERM; sending KILL..."
      kill -KILL "$SERVER_PID" >/dev/null 2>&1 || true
    fi
    wait "$SERVER_PID" >/dev/null 2>&1 || true
  fi
}

trap cleanup_server EXIT

if ! command -v curl >/dev/null 2>&1; then
  echo "'curl' is required to check FastAPI readiness." | tee "$REPORT_FILE"
  exit 2
fi

echo "Starting FastAPI server from $APP_DIR/main.py..."
(
  cd "$APP_DIR"
  exec python3 main.py
) >"$SERVER_LOG_FILE" 2>&1 &
SERVER_PID=$!

echo "Waiting for FastAPI server at $SERVER_URL..."
for _ in $(seq 1 30); do
  if curl -fsS "$SERVER_OPENAPI_URL" >/dev/null 2>&1; then
    echo "FastAPI server is up."
    break
  fi
  sleep 1
done

if ! curl -fsS "$SERVER_OPENAPI_URL" >/dev/null 2>&1; then
  echo "FastAPI server did not become ready. Check $SERVER_LOG_FILE" | tee "$REPORT_FILE"
  exit 1
fi

if command -v psql >/dev/null 2>&1 && [[ -n "${DB_HOST:-}" ]] && [[ -n "${DB_PORT:-}" ]] && [[ -n "${DB_NAME:-}" ]] && [[ -n "${DB_USERNAME:-}" ]] && [[ -n "${DB_PASSWORD:-}" ]]; then
  echo "Executing pre-test DB cleanup..."
  if PGPASSWORD="$DB_PASSWORD" psql \
    --host="$DB_HOST" \
    --port="$DB_PORT" \
    --username="$DB_USERNAME" \
    --dbname="$DB_NAME" \
    --file="$PRE_CLEAN_SQL" \
    >/dev/null; then
    echo "Pre-test DB cleanup completed."
  else
    echo "Pre-test DB cleanup failed. Continuing to collection run."
  fi
else
  echo "Skipping pre-test DB cleanup (missing psql or DB_* settings)."
fi

if command -v newman >/dev/null 2>&1; then
  newman run "$COLLECTION_FILE" \
    --reporters cli \
    | tee "$REPORT_FILE"
  exit ${PIPESTATUS[0]}
fi

if command -v postman >/dev/null 2>&1; then
  postman collection run "$COLLECTION_FILE" -r cli | tee "$REPORT_FILE"
  exit ${PIPESTATUS[0]}
fi

echo "Neither 'newman' nor 'postman' CLI is installed." | tee "$REPORT_FILE"
echo "Install one of them to execute the collection from terminal." | tee -a "$REPORT_FILE"
echo "You can still run the collection from Postman UI Collection Runner." | tee -a "$REPORT_FILE"
exit 2
