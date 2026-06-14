.PHONY: install run test lint typecheck verify docker contract-test

install:
	python -m pip install -e ".[dev]"

run:
	uvicorn medintelos.api.app:app --reload --port 8080

test:
	pytest

lint:
	ruff check .

typecheck:
	mypy src/medintelos

verify: lint test

docker:
	docker compose up --build

contract-test:
	npm test
