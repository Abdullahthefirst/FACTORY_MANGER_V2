"""Update helpers for corrections and approval actions."""

from __future__ import annotations

from typing import Any

from src.database.inserts import insert_record, write_audit


def update_record(client: Any, table_name: str, record_id: str, payload: dict[str, Any]):
    return (
        client.table(table_name)
        .update(payload)
        .eq("id", record_id)
        .execute()
    )


def apply_inventory_movement(client: Any, payload: dict[str, Any]) -> str | None:
    """Write a movement and keep the corresponding inventory balance in sync."""
    material_id = payload.get("material_id")
    location = payload.get("warehouse_location", "Main warehouse")
    quantity = float(payload.get("quantity", 0) or 0)
    movement_type = str(payload.get("movement_type", "")).lower()
    delta = quantity if movement_type in {"receipt", "adjustment"} else -quantity if movement_type == "consumption" else 0
    rows = []
    if material_id and delta:
        current = (
            client.table("inventory")
            .select("id, quantity")
            .eq("material_id", material_id)
            .eq("warehouse_location", location)
            .limit(1)
            .execute()
        )
        rows = current.data or []
        if rows:
            new_quantity = float(rows[0].get("quantity", 0) or 0) + delta
            if new_quantity < 0:
                raise ValueError("This consumption would make inventory negative.")
    created = insert_record(client, "inventory_movements", payload)
    if material_id and delta:
        if rows:
            new_quantity = float(rows[0].get("quantity", 0) or 0) + delta
            update_record(client, "inventory", rows[0]["id"], {"quantity": new_quantity})
        else:
            insert_record(client, "inventory", {"material_id": material_id, "quantity": delta, "warehouse_location": location})
    return created[0].get("id") if created else None


def approve_submission(client: Any, submission_id: str, reviewer_id: str):
    return (
        client.table("data_entry_submissions")
        .update({"status": "approved", "reviewed_by": reviewer_id})
        .eq("id", submission_id)
        .execute()
    )


ALLOWED_SUBMISSION_TABLES = {
    "production_records",
    "inventory_movements",
    "maintenance_records",
    "quality_inspections",
    "employee_attendance",
    "shipments",
}


def apply_submission(client: Any, submission_id: str, reviewer_id: str, approve: bool, note: str = "") -> None:
    """Approve/reject a submission and apply only whitelisted operational writes."""
    response = client.table("data_entry_submissions").select("*").eq("id", submission_id).single().execute()
    submission = response.data or {}
    target_table = submission.get("target_table")
    if target_table not in ALLOWED_SUBMISSION_TABLES:
        raise ValueError("This submission targets an unsupported table.")

    from datetime import datetime, timezone

    if approve:
        payload = dict(submission.get("payload") or {})
        if target_table == "shipments" and payload.get("shipment_id"):
            shipment_id = payload.pop("shipment_id")
            payload.pop("note", None)
            payload.pop("updated_by", None)
            update_record(client, target_table, shipment_id, payload)
            record_id = shipment_id
        else:
            payload.pop("shipment_id", None)
            payload.pop("note", None)
            payload.pop("updated_by", None)
            if target_table == "inventory_movements":
                record_id = apply_inventory_movement(client, payload)
            else:
                created = insert_record(client, target_table, payload)
                record_id = created[0].get("id") if created else None
        new_status = "approved"
    else:
        record_id = None
        new_status = "rejected"

    client.table("data_entry_submissions").update({
        "status": new_status,
        "reviewed_by": reviewer_id,
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
        "review_note": note or None,
    }).eq("id", submission_id).execute()
    write_audit(client, new_status, target_table, record_id, reviewer_id, {"submission_id": submission_id})
