# NITMEXS

## Additional Integration Notes

- Proctor event stream cursor polling:
  - `PROCTOR_EVENT_STREAM_INTEGRATION.md`
- Proctor alert lifecycle endpoints:
  - `POST /admin/proctor/alerts/sync`
  - `GET /admin/proctor/alerts`
  - `GET /admin/proctor/alerts/summary`
  - `GET /admin/proctor/alerts/metrics`
  - `GET /admin/exams/{exam_id}/proctor-alerts/live`
  - `POST /admin/proctor/alerts/{alert_id}/acknowledge`
  - `POST /admin/proctor/alerts/{alert_id}/resolve`

## Windows Packaging (PyInstaller + Inno Setup)

This repository includes packaging templates for both server and desktop client.

### 1) Build executables with PyInstaller

From repository root:

```bash
pyinstaller packaging/server.spec
pyinstaller packaging/client.spec
```

Expected outputs:

- `dist/NITMEXS-Server.exe`
- `dist/NITMEXS-Client.exe`

### 2) External runtime configuration (server)

The server keeps runtime config external to the executable.

- Example config template: `packaging/nitmexs.example.yaml`
- Installer copies this as `nitmexs.yaml` on first install.
- You can also use env vars (`NITMEXS_HOST`, `NITMEXS_PORT`, `NITMEXS_DB_PATH`, etc.).

Notes:

- DB path remains configurable via config/env.
- Logging paths remain configurable via config/env.
- Log directories are auto-created by logging initialization.

### 3) Generate Windows installers with Inno Setup

Templates provided:

- Server: `packaging/inno/server_installer.iss`
- Client: `packaging/inno/client_installer.iss`

In Inno Setup Compiler:

1. Open the `.iss` file.
2. Update `AppVersion` and file paths if needed.
3. Compile installer.

### 4) Server launch modes (future service compatibility)

Server launcher:

```bash
python -m phase1_server.server_entry --mode foreground
python -m phase1_server.server_entry --mode service
```

Current behavior:

- `foreground` starts uvicorn normally.
- `service` currently delegates to normal startup, but provides a stable hook for future Windows Service integration.

