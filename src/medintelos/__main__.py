"""Run the development API with ``python -m medintelos``."""

import uvicorn


def main() -> None:
    uvicorn.run("medintelos.api.app:app", host="0.0.0.0", port=8080, reload=False)


if __name__ == "__main__":
    main()
