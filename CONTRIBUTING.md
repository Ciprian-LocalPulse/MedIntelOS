# Contributing

Thank you for improving MedIntelOS. Contributions should keep the project
testable, transparent about limitations, and safe for public distribution.

## Development

1. Create a virtual environment.
2. Run `python -m pip install -e ".[dev]"`.
3. Create a focused branch and add tests with the change.
4. Run `ruff check .`, `pytest`, and `mypy src/medintelos`.
5. For contract changes, run `npm test`.

## Clinical Changes

Clinical rules must include a primary published source, units, inclusion and
exclusion criteria, missing-data behavior, and tests at every threshold. A rule
implementation is not clinical validation. Do not describe it as validated,
safe, compliant, or ready for patient care without publicly reviewable evidence.

## Scope and Priority

Check `docs/ROADMAP.md` before starting non-trivial work — it lists the
current milestone and what is intentionally deferred. `docs/GOVERNANCE.md`
covers versioning, release process, and review expectations. If your change
doesn't fit an open roadmap item, open an issue first so scope is agreed
before code is written.

## Pull Requests

Keep changes narrow. Explain behavior, risks, test evidence, migration impact,
and any security or privacy consequences. Never commit real patient data,
credentials, private keys, model artifacts derived from PHI, or licensed
terminology content that cannot be redistributed.
