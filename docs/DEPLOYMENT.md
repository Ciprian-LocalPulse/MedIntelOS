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
| `MEDINTELOS_AUDIT_BACKEND` | `memory` or `postgres` | `memory` |
| `MEDINTELOS_OAUTH_ENABLED` | Enable Bearer JWT auth alongside API key | `false` |
| `MEDINTELOS_OAUTH_ISSUER` | Expected `iss` claim; required if OAuth enabled | unset |
| `MEDINTELOS_OAUTH_AUDIENCE` | Expected `aud` claim; required if OAuth enabled | unset |
| `MEDINTELOS_OAUTH_JWKS_URL` | JWKS endpoint; required if OAuth enabled | unset |
| `MEDINTELOS_OAUTH_JWKS_CACHE_SECONDS` | JWKS cache TTL | `300` |
| `MEDINTELOS_RATE_LIMIT_ENABLED` | Enable per-client rate limiting | `true` |
| `MEDINTELOS_RATE_LIMIT_REQUESTS_PER_MINUTE` | Sustained rate per client | `120` |
| `MEDINTELOS_RATE_LIMIT_BURST` | Burst capacity per client | `20` |

Production mode refuses the built-in API key and requires at least 24 characters.
This length check is only a configuration guard, not a credential-management
solution.

## OAuth2/OIDC Authentication

The API key remains the default and is treated as a trusted system-level
credential with unrestricted access — nothing changes for existing
deployments. Setting `MEDINTELOS_OAUTH_ENABLED=true` additionally accepts
`Authorization: Bearer <jwt>`, validated against `MEDINTELOS_OAUTH_JWKS_URL`
(RS256 only). An OAuth-authenticated caller is scope-limited per request; an
API-key caller is not — see `api/auth.py`'s module docstring for why that
split exists and what it does not yet cover (full SMART App Launch is
0.5.0).

### Scopes

FHIR routes enforce SMART v1-style scopes from the token's `scope` claim:

- `<compartment>/<resourceType>.<action>`, e.g. `patient/Observation.read`
- `*` is accepted for the resource (`patient/*.read`) or the action
  (`user/Patient.*`)
- A `write` scope also satisfies a `read` check
- The compartment (`patient`/`user`/`system`) is accepted but not yet
  enforced distinctly — every compartment behaves the same today

A request without sufficient scope gets `403`, not `401` — the token is
valid, it just doesn't authorize this action.

### Trying it against a real identity provider

Any standards-compliant OIDC provider works (Keycloak, Auth0, Okta, etc.).
Point `MEDINTELOS_OAUTH_JWKS_URL` at its JWKS endpoint (commonly
`<issuer>/.well-known/jwks.json` or `<issuer>/protocol/openid-connect/certs`
for Keycloak), and set `MEDINTELOS_OAUTH_ISSUER` / `MEDINTELOS_OAUTH_AUDIENCE`
to match how that provider issues tokens. `tests/test_oauth.py` and
`tests/test_api_oauth.py` show the exact claim shape expected, using a
locally generated key instead of a real provider.

## Rate Limiting

Enabled by default. An in-memory token-bucket limiter keys on the presented
credential (API key or bearer token value) when present, falling back to
client IP otherwise. `/health` is never limited. Exceeding the limit returns
`429` with a `Retry-After` header.

**Boundary:** the limiter's state lives in one process. Running multiple API
instances behind a load balancer means each instance enforces the configured
limit independently — the effective ceiling across the fleet is
`instances × MEDINTELOS_RATE_LIMIT_REQUESTS_PER_MINUTE`, not a global cap. A
shared limiter (Redis-backed token bucket, or similar) is required before
that matters; not yet implemented.

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

## FHIR Interoperability (0.5.0)

### `$validate`

`POST /fhir/R5/{resourceType}/$validate` checks required elements (per the
FHIR R5 base spec) and, for vital-signs Observations, the LOINC code
against a small local table. Returns an `OperationOutcome`; never persists
anything. **This is not US Core or IPS conformance** — neither IG has a
published FHIR R5 version as of this writing, so validating against either
would misrepresent what's actually being checked. See
`fhir/validation.py`'s module docstring for exact scope.

### SMART App Launch (resource-server side)

With `MEDINTELOS_OAUTH_ENABLED=true`:
- `GET /fhir/R5/.well-known/smart-configuration` — discovery document.
  Set `MEDINTELOS_OAUTH_AUTHORIZATION_ENDPOINT` and
  `MEDINTELOS_OAUTH_TOKEN_ENDPOINT` so it advertises your actual identity
  provider's endpoints — MedIntelOS validates tokens, it doesn't issue them,
  so it can't derive these on its own.
- The `CapabilityStatement` (`GET /fhir/R5/metadata`) carries the same
  information via the `oauth-uris` extension for clients that discover via
  CapabilityStatement instead of `.well-known`.
- A token with a `patient` claim (SMART launch context) restricts that
  caller's `read`/search to the named patient's compartment — a request for
  another patient's data returns `403`, and search results are filtered
  rather than erroring. **Not yet enforced on create/update/delete** — see
  `api/auth.py`'s `patient_compartment_permits` docstring.
- A token's `fhirUser` claim, when present, is available on `AuthContext`
  but not yet used anywhere further.

### `$export` (Bulk Data)

```
GET /fhir/R5/$export                    # every resource type
GET /fhir/R5/{resourceType}/$export     # one resource type
```

Both require `Prefer: respond-async`. Response is `202` with a
`Content-Location` pointing at the status endpoint:

```
GET /fhir/R5/$export-status/{job_id}      # manifest once ready
GET /fhir/R5/$export-files/{job_id}/{Type}.ndjson   # download
DELETE /fhir/R5/$export-status/{job_id}   # cancel
```

System-level `$export` requires a full-access (API-key) credential — an
OAuth-scoped client gets `403` and should use the type-level export for
whichever resource type its scope actually covers.

**Boundary:** jobs run synchronously at kick-off and live in process memory
only (`fhir/bulk_export.py`). They do not survive a restart, are not shared
across multiple API instances, and this is not sized for large datasets. A
production Bulk Data deployment needs a real background job queue and
durable/object storage for the NDJSON output — not implemented here.

## Production Readiness Gate

Do not expose the reference container to patient data. `MEDINTELOS_FHIR_BACKEND=postgres`
replaces volatile storage, `MEDINTELOS_OAUTH_ENABLED=true` plus rate
limiting cover authentication and abuse throttling for a single instance,
and `$validate`/`$export` add interoperability surface — but a production
program must still add TLS termination, adopt a real terminology server and
a published conformance profile once one exists for R5, encrypt durable
data at rest, isolate tenants, automate and test backups beyond the manual
`pg_dump` steps above, add a shared (multi-instance) rate limiter and a
durable/shared `$export` job backend, extend patient-compartment
enforcement to writes, monitor security events, and complete clinical and
regulatory validation (0.6.0).

## Contract Deployment

Use a development chain first. Pin compiler and dependency hashes, run static
analysis, commission an independent audit, define upgrade and pause strategy,
use a multisig administrator, test key loss, and review all events for privacy.

The contract records erasure evidence; it cannot erase off-chain replicas or
immutable blockchain history. Do not market that event as proof of legal erasure.
