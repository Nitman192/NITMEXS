"""Server process entrypoint with future-compatible service mode hooks."""

from __future__ import annotations

import argparse
import logging

import uvicorn

from phase1_server.logging_config import configure_logging
from phase1_server.services.maintenance_service import MaintenanceService, RestoreValidationError
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


def run_backup_mode() -> int:
    settings = load_settings()
    configure_logging(settings)
    logger = logging.getLogger("phase1_server")

    service = MaintenanceService(settings.db_path, logger=logger)
    backup_path = service.backup_database()
    logger.info("backup_mode_completed", extra={"backup_path": str(backup_path)})
    return 0


def run_restore_mode(restore_path: str) -> int:
    settings = load_settings()
    configure_logging(settings)
    logger = logging.getLogger("phase1_server")

    service = MaintenanceService(settings.db_path, logger=logger)
    try:
        service.restore_database(restore_path)
    except RestoreValidationError as exc:
        logger.error("restore_mode_failed", extra={"error": str(exc)})
        return 2

    logger.info("restore_mode_completed", extra={"restore_source": restore_path})
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="NITMEXS server launcher")
    parser.add_argument(
        "--mode",
        choices=["foreground", "service"],
        default="foreground",
        help="Run mode. 'service' is future-compatible for service wrappers.",
    )
    parser.add_argument(
        "--backup",
        action="store_true",
        help="Create timestamped SQLite backup in data/backups.",
    )
    parser.add_argument(
        "--restore",
        metavar="PATH",
        help="Restore SQLite database from backup path after schema validation.",
    )
    args = parser.parse_args()

    if args.backup and args.restore:
        parser.error("--backup and --restore are mutually exclusive")

    if args.backup:
        return run_backup_mode()
    if args.restore:
        return run_restore_mode(args.restore)

    if args.mode == "service":
        run_service_mode()
    else:
        run_foreground()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
