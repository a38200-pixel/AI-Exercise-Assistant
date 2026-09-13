"""Production entry point that honors a cloud provider's PORT variable."""

from __future__ import annotations

import os

import uvicorn


def get_port() -> int:
    raw_port = os.getenv("PORT", "8000")
    try:
        port = int(raw_port)
    except ValueError as exc:
        raise RuntimeError("PORT must be an integer.") from exc
    if not 1 <= port <= 65535:
        raise RuntimeError("PORT must be between 1 and 65535.")
    return port


def main() -> None:
    uvicorn.run(
        "backend.app.main:app",
        host="0.0.0.0",
        port=get_port(),
        reload=False,
        log_level=os.getenv("LOG_LEVEL", "info").lower(),
    )


if __name__ == "__main__":
    main()
