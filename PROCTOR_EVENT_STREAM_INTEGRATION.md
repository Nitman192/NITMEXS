# Proctor Event Stream Integration (Cursor-Based)

This guide shows how to consume:

- `GET /admin/proctor/events`

with cursor-token polling (`created_at + event_id`) for exact continuation.

## Why this matters

- No duplicate events on refresh loops.
- No missed events when multiple events share the same timestamp.
- Safe resume after client restart by persisting `next_cursor`.
- Lower client complexity than manual timestamp dedupe logic.

## Request contract

Query params:

- `limit` (optional, default `100`, max `500`)
- `exam_id` (optional, filter by exam)
- `cursor` (preferred for continuation)
- `since` (legacy fallback, do not send with `cursor`)

Important:

- Send either `cursor` or `since`, not both.

## Response contract

`data` includes:

- `events`: ordered by `(created_at, event_id)` ascending
- `next_cursor`: use this for next poll
- `next_since`: backward-compatible timestamp cursor
- `count`, `limit`, `as_of`, `exam_id`

## Recommended client flow

1. Load `saved_cursor` from local storage (file/settings/db).
2. First call:
   - if `saved_cursor` exists, call with `cursor=saved_cursor`
   - else call without cursor (or with optional `since`)
3. Apply events in returned order.
4. Persist `next_cursor` immediately after successful processing.
5. Repeat polling every 1-2 seconds (LAN) with backoff on failures.

## Minimal Python-style example

```python
import time
import httpx

BASE_URL = "http://127.0.0.1:8000"
HEADERS = {"x-admin": "true"}

def load_cursor() -> str | None:
    try:
        with open("proctor_cursor.txt", "r", encoding="utf-8") as f:
            value = f.read().strip()
            return value or None
    except FileNotFoundError:
        return None

def save_cursor(cursor: str | None) -> None:
    if cursor is None:
        return
    with open("proctor_cursor.txt", "w", encoding="utf-8") as f:
        f.write(cursor)

def process_event(event: dict) -> None:
    # Update dashboard state, counters, timeline, alerts, etc.
    pass

cursor = load_cursor()
backoff_seconds = 1.0

while True:
    params = {"limit": 200}
    if cursor:
        params["cursor"] = cursor

    try:
        response = httpx.get(
            f"{BASE_URL}/admin/proctor/events",
            headers=HEADERS,
            params=params,
            timeout=5.0,
        )
        response.raise_for_status()
        payload = response.json()["data"]

        for event in payload["events"]:
            process_event(event)

        cursor = payload.get("next_cursor") or cursor
        save_cursor(cursor)
        backoff_seconds = 1.0
        time.sleep(1.0)
    except Exception:
        time.sleep(backoff_seconds)
        backoff_seconds = min(backoff_seconds * 2, 10.0)
```

## Operational notes

- On `400` invalid cursor:
  - clear local cursor
  - restart from blank cursor or trusted `since`
- On `404` with `exam_id`:
  - exam may be deleted or closed out of scope; remove exam filter or refresh exam list
- Keep event application idempotent in UI/state reducers for extra safety.
