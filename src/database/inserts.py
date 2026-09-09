"""Safe insert and audit helpers for the data-entry application."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def insert_record(client: Any, table_name: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
    response = client.table(table_name).insert(payload).execute()
    return response.data or []


def create_submission(
    client: Any,
    entry_type: str,
    target_table: str,
    payload: dict[str, Any],
    submitted_by: str | None,
) -> list[dict[str, Any]]:
    submission = {
        "entry_type": entry_type,
        "target_table": target_table,
        "payload": payload,
        "submitted_by": submitted_by,
        "status": "submitted",
        "submitted_at": datetime.now(timezone.utc).isoformat(),
    }
    return insert_record(client, "data_entry_submissions", submission)


def write_audit(
    client: Any,
    action: str,
    table_name: str,
    record_id: str | None,
    actor_id: str | None,
    details: dict[str, Any] | None = None,
) -> None:
    try:
        insert_record(
            client,
            "audit_log",
            {
                "action": action,
                "table_name": table_name,
                "record_id": record_id,
                "actor_id": actor_id,
                "details": details or {},
            },
        )
    except Exception:
        # An audit failure must not cause a successful operational entry to look failed.
        pass
