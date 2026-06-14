$ErrorActionPreference = "Stop"
python -m ruff check .
python -m pytest
python -m mypy src/medintelos
Write-Host "Python verification passed."
