#!/usr/bin/env sh
set -eu
python -m ruff check .
python -m pytest
python -m mypy src/medintelos
printf '%s\n' "Python verification passed."
