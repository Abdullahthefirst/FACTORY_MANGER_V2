"""Validation rules used before any operator submission is written."""

from __future__ import annotations

from datetime import date
from typing import Any


def positive_number(value: Any, label: str) -> tuple[bool, str]:
    try:
        if float(value) < 0:
            return False, f"{label} cannot be negative."
    except (TypeError, ValueError):
        return False, f"{label} must be a number."
    return True, ""


def validate_production(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field, label in [
        ("planned_quantity", "Planned quantity"),
        ("actual_quantity", "Actual quantity"),
        ("rejected_quantity", "Rejected quantity"),
        ("downtime_minutes", "Downtime"),
    ]:
        ok, message = positive_number(payload.get(field, 0), label)
        if not ok:
            errors.append(message)
    actual = float(payload.get("actual_quantity", 0) or 0)
    rejected = float(payload.get("rejected_quantity", 0) or 0)
    if rejected > actual:
        errors.append("Rejected quantity cannot exceed actual quantity.")
    return errors


def validate_attendance(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    overtime = payload.get("overtime_hours", 0) or 0
    ok, message = positive_number(overtime, "Overtime hours")
    if not ok:
        errors.append(message)
    attendance_date = payload.get("attendance_date")
    if isinstance(attendance_date, date) and attendance_date > date.today():
        errors.append("Attendance date cannot be in the future.")
    return errors


def validate_required(payload: dict[str, Any], fields: dict[str, str]) -> list[str]:
    return [
        label
        for field, label in fields.items()
        if payload.get(field) in (None, "", [])
    ]
