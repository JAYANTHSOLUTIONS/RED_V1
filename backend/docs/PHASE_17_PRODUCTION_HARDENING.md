# RED_V1 — Phase 17 Production Hardening & Operations Guide

## 1. Overview & Scope

This document provides complete production operational guidance for the **RED_V1** Tamil Nadu Real-Estate Consultant & Brokerage platform.
It details:
1. Production Configuration & Secret Management
2. Production Deployment Checklist
3. Fail-Fast Validation & Insecure Defaults Rejection
4. PostgreSQL Backup & Point-In-Time Restore (PITR) Runbook
5. Health Probes & Monitoring Strategy
6. Rate Limiting, Abuse Prevention & Capacity Controls

---

## 2. Production Deployment Checklist

Before deploying RED_V1 to a staging or production environment, verify every item below:

| Category | Check | Verification Method / Requirement |
| :--- | :--- | :--- |
| **Environment** | `APP_ENV` set to `production` | Rejects weak secrets, enables HSTS, disables `/docs` |
| **Debug Mode** | `DEBUG` set to `False` | Startup fails if `DEBUG=True` when `APP_ENV=production` |
| **JWT Secrets** | `JWT_SECRET_KEY` length >= 32 | Must be a high-entropy string (e.g. `openssl rand -hex 32`) |
| **CORS Origins** | `CORS_ALLOWED_ORIGINS` specified | Must list explicit domain(s), no wildcard `*` allowed |
| **Database Pool**| `DB_POOL_SIZE` & `DB_MAX_OVERFLOW` | Configured according to database max connections |
| **Storage Backend** | `STORAGE_BACKEND` set to `s3` or `local` | If `s3`, bucket and credentials must be populated |
| **OpenAPI Docs**| `/docs`, `/redoc`, `/openapi.json` | Returns 404 in production unless `OPENAPI_DOCS_ENABLED=True` |
| **Health Probes** | `/health/live` & `/health/ready` | Wired to container orchestrator / load balancer |
| **Rate Limiter**| `RATE_LIMIT_LOGIN_ATTEMPTS` | Sliding window protects against brute force attacks |
| **Backup Runbook** | PostgreSQL backup automation active | Daily `pg_dump` + WAL archiving configured |

---

## 3. Production Environment Configuration (`.env.production`)

```bash
# Application Environment
APP_NAME="Real-Estate Consultant API"
APP_ENV="production"
DEBUG="False"
API_V1_PREFIX="/api/v1"

# Production Secret Key (Generate with: openssl rand -hex 32)
JWT_SECRET_KEY="REPLACE_WITH_EXACT_64_CHAR_HEX_ENTROPY_STRING_NEVER_CHECK_IN"
JWT_ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=20
REFRESH_TOKEN_EXPIRE_DAYS=14

# Production PostgreSQL Database
DATABASE_URL="postgresql+asyncpg://red_admin:SECURE_DB_PASSWORD@prod-db.internal:5432/red_v1_prod"
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_POOL_TIMEOUT=10
DB_POOL_RECYCLE=1800
DB_ECHO=False

# Explicit CORS Allowlist (No Wildcards in Production)
CORS_ALLOWED_ORIGINS="https://red.jayanthsolutions.com,https://admin.jayanthsolutions.com"

# Storage Backend (S3 or compliant object store)
STORAGE_BACKEND="s3"
STORAGE_PROVIDER="s3"
STORAGE_BUCKET="red-v1-production-documents"
STORAGE_REGION="ap-south-1"
STORAGE_ENDPOINT_URL="https://s3.ap-south-1.amazonaws.com"
STORAGE_ACCESS_KEY="AKIA_PRODUCTION_ACCESS_KEY"
STORAGE_SECRET_KEY="PRODUCTION_SECRET_KEY"

# File Upload Limits
MAX_UPLOAD_SIZE_MB=15
MAX_DOCUMENT_SIZE_MB=15

# Logging & Monitoring
LOG_LEVEL="INFO"
LOG_FORMAT="json"

# SMTP Notifications (Phase 12)
SMTP_HOST="smtp.mailgun.org"
SMTP_PORT=587
SMTP_USERNAME="postmaster@mg.jayanthsolutions.com"
SMTP_PASSWORD="PRODUCTION_SMTP_PASSWORD"
SMTP_FROM="noreply@jayanthsolutions.com"
SMTP_USE_TLS="True"
SMTP_TIMEOUT_SECONDS=10

# Resilience & Security
EXTERNAL_REQUEST_TIMEOUT=10
IDEMPOTENCY_EXPIRE_HOURS=24
RATE_LIMIT_LOGIN_ATTEMPTS=10
RATE_LIMIT_LOGIN_WINDOW_SECONDS=60
OPENAPI_DOCS_ENABLED="False"
```

---

## 4. PostgreSQL Production Backup & Restore Runbook

### 4.1 Backup Strategy Overview
The PostgreSQL database for RED_V1 contains property listings, client PII, legal document metadata, verification audit records, and financial transaction trails.
A 3-tier backup strategy is recommended:
1. **Automated Daily Logical Backups** (`pg_dump` compressed).
2. **Continuous Write-Ahead Log (WAL) Archiving** for Point-In-Time-Recovery (PITR).
3. **Automated Weekly Restore Testing** into an isolated staging environment.

### 4.2 Automated Logical Backup (`pg_dump`)
Run daily at off-peak hours (e.g. 02:00 IST):

```bash
#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="/var/backups/postgresql"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/red_v1_prod_${TIMESTAMP}.dump"

mkdir -p "${BACKUP_DIR}"

# Execute custom-format compressed backup
PGPASSWORD="${DB_PASSWORD}" pg_dump \
  -h "${DB_HOST}" \
  -p 5432 \
  -U "${DB_USER}" \
  -F c \
  -b \
  -v \
  -f "${BACKUP_FILE}" \
  "${DB_NAME}"

# Encrypt backup with GPG
gpg --encrypt --recipient ops@jayanthsolutions.com "${BACKUP_FILE}"
rm -f "${BACKUP_FILE}"

# Sync encrypted backup to off-site cold storage (e.g. AWS S3 Glacier)
aws s3 cp "${BACKUP_FILE}.gpg" s3://red-v1-backups/database/

# Retain local backups for 14 days
find "${BACKUP_DIR}" -type f -name "*.dump.gpg" -mtime +14 -delete
```

### 4.3 Disaster Recovery Restore Procedure (`pg_restore`)
To restore a logical backup into a clean or disaster-recovery database instance:

```bash
#!/usr/bin/env bash
set -euo pipefail

RESTORE_FILE="$1" # Path to decrypted .dump file
TARGET_DB="red_v1_prod"

echo "=== Commencing RED_V1 Database Restore ==="

# 1. Terminate existing client connections
psql -h "${DB_HOST}" -U "${DB_USER}" -d postgres -c \
  "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${TARGET_DB}' AND pid <> pg_backend_pid();"

# 2. Drop and recreate database
psql -h "${DB_HOST}" -U "${DB_USER}" -d postgres -c "DROP DATABASE IF EXISTS ${TARGET_DB};"
psql -h "${DB_HOST}" -U "${DB_USER}" -d postgres -c "CREATE DATABASE ${TARGET_DB} OWNER ${DB_USER};"

# 3. Restore schema and data with parallel workers
pg_restore \
  -h "${DB_HOST}" \
  -p 5432 \
  -U "${DB_USER}" \
  -d "${TARGET_DB}" \
  -v \
  --no-owner \
  --role="${DB_USER}" \
  "${RESTORE_FILE}"

echo "=== Restore completed successfully. Running post-restore verification ==="
psql -h "${DB_HOST}" -U "${DB_USER}" -d "${TARGET_DB}" -c "SELECT count(*) FROM users;"
psql -h "${DB_HOST}" -U "${DB_USER}" -d "${TARGET_DB}" -c "SELECT count(*) FROM properties;"
```

### 4.4 Point-In-Time Recovery (PITR) Setup
In `postgresql.conf`:
```ini
wal_level = replica
archive_mode = on
archive_command = 'test ! -f /mnt/wal_archive/%f && cp %p /mnt/wal_archive/%f'
archive_timeout = 300
```
In case of accidental corruption at `2026-09-07 14:30:00 IST`, point-in-time recovery can be targeted to `2026-09-07 14:29:50 IST` by placing `recovery.signal` and setting `recovery_target_time = '2026-09-07 14:29:50+05:30'`.

---

## 5. Health Probes & Load Balancer Integration

The application provides two operational endpoints:

1. **`GET /health/live` (or `/health`)**:
   - Returns HTTP 200 `{"status": "alive"}` whenever the ASGI process is up.
   - Used by Kubernetes `livenessProbe` or AWS Target Group health check.
   - Does not query external dependencies.

2. **`GET /health/ready` (or `/ready`)**:
   - Returns HTTP 200 `{"data": {"database": "ok"}, "message": "Service is ready."}` when all critical infrastructure dependencies are verified.
   - If the database connection is dropped or pool exhausted, returns HTTP 503 `SERVICE_UNAVAILABLE` without exposing database host, port, or exception traces.
   - Used by Kubernetes `readinessProbe` to remove instance from active traffic rotation during network blips or failovers.

---

## 6. Correlation Tracing & Log Ingestion

1. **Request Correlation (`X-Request-ID`)**:
   - Every inbound request is assigned a sanitized correlation ID conforming to `^[a-zA-Z0-9_\-\.:]{1,64}$`.
   - Propagated through all internal service, repository, and database query log lines.
   - Sent back in the response header `X-Request-ID`.
2. **Health Spam Suppression**:
   - Successful health checks (< 400) emit at `DEBUG` level to keep production stdout clean.
   - Failed health checks (>= 400) emit at `WARNING`/`ERROR` for incident alert triggers.
3. **Sensitive Data Masking**:
   - `SensitiveDataFilter` masks `Bearer <token>`, `password`, and JWT signatures from log streams before writing to stdout.
