"""Server process entrypoint with future-compatible service mode hooks."""

from __future__ import annotations

import argparse

import uvicorn

from phase1_server.settings import load_settings


def run_foreground() -> None:
    settings = load_settings()
    uvicorn.run(
        "phase1_server.app:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
    )


def run_service_mode() -> None:
    """Background-service compatible launcher path.

    For now this delegates to the same runtime as foreground mode.
    Later this function can be integrated with Windows Service wrappers.
    """

    run_foreground()


def main() -> int:
    parser = argparse.ArgumentParser(description="NITMEXS server launcher")
    parser.add_argument(
        "--mode",
        choices=["foreground", "service"],
        default="foreground",
        help="Run mode. 'service' is future-compatible for service wrappers.",
    )
    args = parser.parse_args()

    if args.mode == "service":
        run_service_mode()
    else:
        run_foreground()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
