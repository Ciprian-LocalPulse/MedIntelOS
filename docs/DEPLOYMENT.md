# Deployment Guide

## Local Evaluation

Use synthetic data only. Set a new API key and run `docker compose up --build`.
The container runs without root privileges, drops Linux capabilities, uses a
read-only root filesystem, and exposes port 8080.

## Configuration

| Variable | Purpose | Default |
|---|---|---|
| `MEDINTELOS_APP_NAME` | Service name | `MedIntelOS` |
| `MEDINTELOS_ENVIRONMENT` | Runtime environment | `development` |
| `MEDINTELOS_API_KEY` | Reference API credential | Unsafe development value |
| `MEDINTELOS_FHIR_BASE_URL` | URLs advertised in metadata | `http://localhost:8080` |
| `MEDINTELOS_REQUIRE_API_KEY` | Enable API-key boundary | `true` |
| `MEDINTELOS_MAX_RESOURCE_BYTES` | HTTP body limit | `1000000` |
| `MEDINTELOS_FHIR_BACKEND` | `memory` or `postgres` | `memory` |
| `MEDINTELOS_DATABASE_URL` | Postgres DSN; required when backend is `postgres` | unset |
| `MEDINTELOS_DATABASE_POOL_MIN_SIZE` | Connection pool floor | `1` |
| `MEDINTELOS_DATABASE_POOL_MAX_SIZE` | Connection pool ceiling | `10` |

Production mode refuses the built-in API key and requires at least 24 characters.
This length check is only a configuration guard, not a credential-management
solution.

## Persistent Storage (Postgres)

The default `memory` backend loses all data on restart — fine for a quick
evaluation, not for anything you want to keep. `postgres` persists resources
in a single-current-version table (see `migrations/versions/0001_fhir_resources.py`);
full FHIR version history is not yet implemented (`docs/ROADMAP.md`, 0.3.0
boundary).

### Local, without Docker

```bash
export MEDINTELOS_DATABASE_URL="postgresql://medintelos:CHANGE-ME@localhost:5432/medintelos"
pip install -e ".[postgres]"
alembic upgrade head          # run once, and again after every migration you add
export MEDINTELOS_FHIR_BACKEND=postgres
uvicorn medintelos.api.app:app --reload
```

### Docker Compose

The default `docker-compose.yml` still uses the in-memory backend — nothing
changes for existing setups. To run with Postgres instead:

```bash
cp .env.example .env
# edit .env: set MEDINTELOS_API_KEY, POSTGRES_PASSWORD, and
# MEDINTELOS_DATABASE_URL's password to match POSTGRES_PASSWORD

docker compose -f docker-compose.yml -f docker-compose.postgres.yml up --build
```

This starts three services: `db` (Postgres, with a named volume so data
survives `docker compose down`), `migrate` (runs `alembic upgrade head` once
and exits — `api` waits for it to succeed before starting), and `api` (now
pointed at `postgres` via `MEDINTELOS_FHIR_BACKEND`).

### Adding a new migration

```bash
alembic revision -m "describe the change"
# edit the generated file in migrations/versions/ by hand — this project
# does not use --autogenerate, so the migration only contains what you
# actually write
alembic upgrade head          # apply and verify locally before committing
```

Always write and test both `upgrade()` and `downgrade()`.

### Backup and restore

The `db` service's data lives in the `medintelos-db-data` named volume. For
anything beyond local evaluation, back up with `pg_dump`, not by copying the
volume directly:

```bash
docker compose exec db pg_dump -U medintelos medintelos > backup.sql
# restore into a fresh database:
docker compose exec -T db psql -U medintelos medintelos < backup.sql
```

Schedule this, store backups off the host running the database, and test
restores — an untested backup is not a backup.

## Production Readiness Gate

Do not expose the reference container to patient data. `MEDINTELOS_FHIR_BACKEND=postgres`
replaces volatile storage, but a production program must still add TLS and an
identity provider (`docs/ROADMAP.md` 0.4.0), enforce authorization per resource
and purpose, validate FHIR profiles and terminology (0.5.0), encrypt durable
data at rest, isolate tenants, automate and test backups beyond the manual
`pg_dump` steps above, monitor security events, and complete clinical and
regulatory validation (0.6.0).

## Contract Deployment

Use a development chain first. Pin compiler and dependency hashes, run static
analysis, commission an independent audit, define upgrade and pause strategy,
use a multisig administrator, test key loss, and review all events for privacy.

The contract records erasure evidence; it cannot erase off-chain replicas or
immutable blockchain history. Do not market that event as proof of legal erasure.
