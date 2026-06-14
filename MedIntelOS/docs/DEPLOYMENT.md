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

Production mode refuses the built-in API key and requires at least 24 characters.
This length check is only a configuration guard, not a credential-management
solution.

## Production Readiness Gate

Do not expose the reference container to patient data. A production program must
replace volatile storage, add TLS and an identity provider, enforce authorization
per resource and purpose, validate FHIR profiles and terminology, encrypt durable
data, isolate tenants, implement backups, monitor security events, and complete
clinical and regulatory validation.

## Contract Deployment

Use a development chain first. Pin compiler and dependency hashes, run static
analysis, commission an independent audit, define upgrade and pause strategy,
use a multisig administrator, test key loss, and review all events for privacy.

The contract records erasure evidence; it cannot erase off-chain replicas or
immutable blockchain history. Do not market that event as proof of legal erasure.
