#!/usr/bin/env bash
# ==============================================================================
# Production Database Migration and Schema Initialization Script
# Handles:
# - Connection pooler compatibility (Neon / Supabase PgBouncer & direct connections)
# - Prisma schema validation and migration execution
# - Safe retry handling with exponential backoff
# ==============================================================================

set -euo pipefail

echo "=================================================="
echo "[DB Migrate] Starting Production Database Migrations"
echo "=================================================="

# Determine workspace root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"

echo "[DB Migrate] Workspace root: ${WORKSPACE_ROOT}"
cd "${WORKSPACE_ROOT}"

# Check required connection string
if [ -z "${DATABASE_URL:-}" ]; then
  if [ -f "${WORKSPACE_ROOT}/.env.production" ]; then
    echo "[DB Migrate] Loading environment variables from .env.production..."
    # shellcheck disable=SC2046
    export $(grep -v '^#' "${WORKSPACE_ROOT}/.env.production" | xargs)
  elif [ -f "${WORKSPACE_ROOT}/.env" ]; then
    echo "[DB Migrate] Loading environment variables from .env..."
    # shellcheck disable=SC2046
    export $(grep -v '^#' "${WORKSPACE_ROOT}/.env" | xargs)
  else
    echo "[DB Migrate] Error: DATABASE_URL is not set and no .env file found."
    exit 1
  fi
fi

# If DIRECT_URL is set (Supabase/Neon direct connection port 5432 vs pooler 6543),
# prefer it for DDL schema migrations to bypass PgBouncer statement locks.
if [ -n "${DIRECT_URL:-}" ]; then
  echo "[DB Migrate] Detected DIRECT_URL for unpooled migration execution."
  MIGRATION_URL="${DIRECT_URL}"
else
  echo "[DB Migrate] Using standard DATABASE_URL."
  MIGRATION_URL="${DATABASE_URL}"
fi

export DATABASE_URL="${MIGRATION_URL}"

# 1. Validate Prisma schema
echo "[DB Migrate] Step 1: Validating Prisma schema..."
pnpm --filter db exec prisma validate

# 2. Generate Prisma Client
echo "[DB Migrate] Step 2: Generating Prisma Client..."
pnpm --filter db exec prisma generate

# 3. Execute production migrations / schema push
echo "[DB Migrate] Step 3: Applying database migrations with connection pool handling..."
MAX_RETRIES=5
RETRY_DELAY=2
COUNT=1

while [ $COUNT -le $MAX_RETRIES ]; do
  echo "[DB Migrate] Attempt ${COUNT} of ${MAX_RETRIES}..."
  if pnpm --filter db exec prisma db push --skip-generate; then
    echo "[DB Migrate] Successfully synchronized database schema!"
    break
  else
    if [ $COUNT -eq $MAX_RETRIES ]; then
      echo "[DB Migrate] Error: Failed to execute database migrations after ${MAX_RETRIES} attempts."
      exit 1
    fi
    echo "[DB Migrate] Transient connection failure. Retrying in ${RETRY_DELAY} seconds..."
    sleep $RETRY_DELAY
    COUNT=$((COUNT + 1))
    RETRY_DELAY=$((RETRY_DELAY * 2))
  fi
done

echo "=================================================="
echo "[DB Migrate] Database migration completed successfully."
echo "=================================================="

