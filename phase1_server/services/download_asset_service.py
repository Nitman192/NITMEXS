"""Safe admin-side editor for downloadable web assets."""

from __future__ import annotations

import os
import re
from pathlib import Path

from phase1_server.services.audit_service import AuditService


class DownloadAssetError(ValueError):
    pass


class DownloadAssetNotFoundError(DownloadAssetError):
    pass


class DownloadAssetConflictError(DownloadAssetError):
    pass


class DownloadAssetValidationError(DownloadAssetError):
    pass


class DownloadAssetService:
    _TEXT_EXTENSIONS = {
        ".csv": "text/csv",
        ".html": "text/html",
        ".txt": "text/plain",
        ".md": "text/markdown",
        ".yaml": "text/plain",
        ".yml": "text/plain",
    }
    _CORE_ASSETS = {
        "demo_question_bank.csv": {"category": "Templates", "display_name": "Demo Question CSV"},
        "demo_exam_package.csv": {"category": "Templates", "display_name": "Demo Exam Package CSV"},
        "demo_student_ids.csv": {"category": "Templates", "display_name": "Demo Student CSV"},
        "manual_admin.html": {"category": "Manuals", "display_name": "Admin Manual"},
        "manual_student.html": {"category": "Manuals", "display_name": "Student Instructions"},
        "manual_examiner.html": {"category": "Manuals", "display_name": "Examiner Review Guide"},
        "manual_backup_restore.html": {
            "category": "Manuals",
            "display_name": "Backup / Restore Guide",
        },
        "manual_offline_ai.html": {"category": "Manuals", "display_name": "Offline AI Setup Guide"},
        "manual_troubleshooting.html": {
            "category": "Manuals",
            "display_name": "Troubleshooting Checklist",
        },
        "release_notes.html": {"category": "System", "display_name": "Release Notes"},
        "nitmexs_config_sample.yaml": {"category": "System", "display_name": "Config Sample"},
    }

    def __init__(self, audit_service: AuditService | None = None):
        self._audit_service = audit_service
        self._web_root = self._resolve_web_root()
        self._custom_root = self._web_root / "custom_downloads"
        self._custom_root.mkdir(parents=True, exist_ok=True)

    def list_assets(self) -> list[dict]:
        rows: list[dict] = []
        for asset_path, meta in self._CORE_ASSETS.items():
            candidate = self._web_root / asset_path
            if not candidate.exists() or not candidate.is_file():
                continue
            rows.append(self._asset_payload(asset_path, candidate, meta["display_name"], meta["category"], False))
        for candidate in sorted(self._custom_root.glob("*")):
            if not candidate.is_file() or candidate.suffix.lower() not in self._TEXT_EXTENSIONS:
                continue
            asset_path = f"custom_downloads/{candidate.name}"
            rows.append(
                self._asset_payload(
                    asset_path,
                    candidate,
                    self._humanize_name(candidate.stem),
                    "Custom",
                    True,
                )
            )
        return rows

    def get_asset(self, asset_path: str) -> dict:
        path = self._resolve_asset(asset_path)
        payload = self._describe_asset(asset_path, path)
        payload["content"] = path.read_text(encoding="utf-8")
        return payload

    def update_asset(self, asset_path: str, content: str, actor_id: str) -> dict:
        path = self._resolve_asset(asset_path)
        path.write_text(self._normalize_content(content), encoding="utf-8")
        payload = self._describe_asset(asset_path, path)
        self._log_event(
            actor_id=actor_id,
            event_type="DOWNLOAD_ASSET_UPDATED",
            payload={"asset_path": asset_path, "file_name": payload["file_name"]},
        )
        return payload

    def create_asset(self, file_name: str, content: str, actor_id: str) -> dict:
        sanitized_name = self._sanitize_file_name(file_name)
        target = (self._custom_root / sanitized_name).resolve()
        if target.exists():
            raise DownloadAssetConflictError("A download file with this name already exists.")
        target.write_text(self._normalize_content(content), encoding="utf-8")
        asset_path = f"custom_downloads/{sanitized_name}"
        payload = self._describe_asset(asset_path, target)
        self._log_event(
            actor_id=actor_id,
            event_type="DOWNLOAD_ASSET_CREATED",
            payload={"asset_path": asset_path, "file_name": sanitized_name},
        )
        return payload

    def _describe_asset(self, asset_path: str, path: Path) -> dict:
        if asset_path in self._CORE_ASSETS:
            meta = self._CORE_ASSETS[asset_path]
            return self._asset_payload(asset_path, path, meta["display_name"], meta["category"], False)
        return self._asset_payload(
            asset_path,
            path,
            self._humanize_name(path.stem),
            "Custom",
            True,
        )

    def _asset_payload(
        self,
        asset_path: str,
        path: Path,
        display_name: str,
        category: str,
        is_custom: bool,
    ) -> dict:
        return {
            "asset_path": asset_path,
            "file_name": path.name,
            "display_name": display_name,
            "category": category,
            "content_type": self._TEXT_EXTENSIONS.get(path.suffix.lower(), "text/plain"),
            "is_custom": is_custom,
            "download_url": f"/web/{asset_path}",
        }

    def _resolve_asset(self, asset_path: str) -> Path:
        normalized = asset_path.strip().replace("\\", "/")
        if normalized in self._CORE_ASSETS:
            candidate = (self._web_root / normalized).resolve()
        elif normalized.startswith("custom_downloads/"):
            candidate = (self._web_root / normalized).resolve()
            if self._custom_root.resolve() not in candidate.parents:
                raise DownloadAssetNotFoundError("Download file not found.")
        else:
            raise DownloadAssetNotFoundError("Download file not found.")
        if not candidate.exists() or not candidate.is_file():
            raise DownloadAssetNotFoundError("Download file not found.")
        if candidate.suffix.lower() not in self._TEXT_EXTENSIONS:
            raise DownloadAssetValidationError("Only text-based download files can be edited here.")
        return candidate

    @classmethod
    def _resolve_web_root(cls) -> Path:
        override = os.environ.get("NITMEXS_WEB_ASSET_ROOT", "").strip()
        if override:
            return Path(override).resolve()
        return Path(__file__).resolve().parents[2] / "phase1_server" / "web"

    @classmethod
    def _normalize_content(cls, content: str) -> str:
        text = str(content or "")
        if len(text) > 200_000:
            raise DownloadAssetValidationError("Please keep the file content within 200000 characters.")
        return text.replace("\r\n", "\n")

    @classmethod
    def _sanitize_file_name(cls, file_name: str) -> str:
        clean = str(file_name or "").strip()
        if not clean:
            raise DownloadAssetValidationError("Please enter a file name.")
        if len(clean) > 120:
            raise DownloadAssetValidationError("Keep the file name within 120 characters.")
        if "/" in clean or "\\" in clean:
            raise DownloadAssetValidationError("Use a file name only, not a folder path.")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", clean):
            raise DownloadAssetValidationError(
                "Use letters, numbers, dot, dash, or underscore in the file name."
            )
        suffix = Path(clean).suffix.lower()
        if suffix not in cls._TEXT_EXTENSIONS:
            raise DownloadAssetValidationError(
                "Supported file types are .html, .csv, .txt, .md, .yaml, and .yml."
            )
        return clean

    @staticmethod
    def _humanize_name(value: str) -> str:
        return value.replace("_", " ").replace("-", " ").strip().title() or "Custom File"

    def _log_event(self, *, actor_id: str, event_type: str, payload: dict) -> None:
        if self._audit_service is None:
            return
        try:
            self._audit_service.log_event(
                entity_type="download_asset",
                entity_id=payload.get("asset_path", "download_asset"),
                actor_type="admin",
                actor_id=actor_id,
                event_type=event_type,
                payload=payload,
            )
        except Exception:
            return
