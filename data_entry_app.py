"""FactoryOps smart data-entry application.

Deploy this file as a second Streamlit Cloud app when operators need a separate
URL. It uses the same Supabase project as ``app.py`` and never stores a local
database or credentials.
"""

from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd
import streamlit as st

from src.database.inserts import create_submission, insert_record, write_audit
from src.database.queries import fetch_table, recent_rows
from src.supabase_client import create_supabase_from_secrets
from src.database.updates import apply_inventory_movement, update_record
from src.database.validators import (
    validate_attendance,
    validate_production,
    validate_required,
)


st.set_page_config(
    page_title="FactoryOps Data Entry",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(
    """
    <style>
    .block-container { max-width: 1300px; padding-top: 2rem; }

    h1, h2, h3 {
        color: var(--text-color, #17324d) !important;
    }

    section[data-testid="stSidebar"] {
        width: 18rem !important;
        min-width: 18rem !important;
        background-color: var(
            --secondary-background-color,
            #f8fafc
        ) !important;
        border-right: 1px solid var(
            --border-color,
            #d7dee8
        ) !important;
    }

    section[data-testid="stSidebar"] > div:first-child {
        width: 18rem !important;
    }

    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] span {
        color: var(--text-color, #17324d) !important;
        opacity: 1 !important;
        visibility: visible !important;
    }

    [data-testid="stSidebar"] [data-testid="stRadio"] {
        width: 100% !important;
    }

    [data-testid="stSidebar"]
    [data-testid="stRadio"]
    [role="radiogroup"] {
        width: 100% !important;
        gap: 0.15rem !important;
    }

    [data-testid="stSidebar"]
    [data-testid="stRadio"]
    [role="radiogroup"] > label {
        display: flex !important;
        align-items: center !important;
        width: 100% !important;
        min-height: 2.6rem !important;
        padding: 0.45rem 0.7rem !important;
        margin: 0.1rem 0 !important;
        border-radius: 0.55rem !important;
        color: var(--text-color, #17324d) !important;
        background: transparent !important;
        overflow: visible !important;
    }

    [data-testid="stSidebar"]
    [data-testid="stRadio"]
    [role="radiogroup"] > label:hover {
        background: var(
            --secondary-background-color,
            #eef2f7
        ) !important;
    }

    [data-testid="stSidebar"]
    [data-testid="stRadio"]
    [role="radiogroup"] > label:has(input:checked) {
        background: color-mix(
            in srgb,
            var(--primary-color, #2563eb) 18%,
            transparent
        ) !important;
        box-shadow: inset 3px 0 0 var(
            --primary-color,
            #2563eb
        ) !important;
    }

    [data-testid="stSidebar"]
    [data-testid="stRadio"]
    label p,
    [data-testid="stSidebar"]
    [data-testid="stRadio"]
    label span,
    [data-testid="stSidebar"]
    [data-testid="stRadio"]
    label div {
        color: var(--text-color, #17324d) !important;
        opacity: 1 !important;
        visibility: visible !important;
        white-space: normal !important;
    }

    [data-testid="stSidebar"] button {
        color: var(--text-color, #17324d) !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def get_client():
    try:
        return create_supabase_from_secrets(st.secrets)
    except Exception as error:
        st.error(str(error))
        st.stop()


supabase = get_client()

if "entry_user" not in st.session_state:
    st.session_state.entry_user = None

if "entry_access_token" in st.session_state:
    try:
        supabase.auth.set_session(
            st.session_state.entry_access_token,
            st.session_state.entry_refresh_token,
        )
    except Exception:
        st.session_state.clear()
        st.rerun()


if st.session_state.entry_user is None:
    st.title("FactoryOps Data Entry")
    st.caption("Secure operational entry for production and support teams.")
    email = st.text_input("Work email")
    password = st.text_input("Password", type="password")
    if st.button("Log in", type="primary"):
        try:
            response = supabase.auth.sign_in_with_password(
                {"email": email, "password": password}
            )
            st.session_state.entry_user = response.user
            st.session_state.entry_access_token = response.session.access_token
            st.session_state.entry_refresh_token = response.session.refresh_token
            st.rerun()
        except Exception as error:
            st.error(f"Login failed: {error}")
    st.stop()


actor_id = getattr(st.session_state.entry_user, "id", None)
actor_email = getattr(st.session_state.entry_user, "email", "")


def label_column(frame: pd.DataFrame) -> str:
    for candidate in [
        "name",
        "full_name",
        "material_name",
        "machine_name",
        "product_name",
        "code",
    ]:
        if candidate in frame.columns:
            return candidate
    return "id"


def select_lookup(
    label: str,
    frame: pd.DataFrame,
    preferred_columns: list[str] | None = None,
    key: str | None = None,
) -> str | None:
    if frame.empty or "id" not in frame.columns:
        st.warning(f"No records are available for {label.lower()}.")
        return None
    columns = preferred_columns or []
    display_column = next(
        (column for column in columns if column in frame.columns),
        label_column(frame),
    )
    choices = {
        f"{row.get(display_column, '')}"
        + (
            f" · {row.get('employee_code', '')}"
            if row.get("employee_code")
            else f" · {row.get('material_code', '')}"
            if row.get("material_code")
            else f" · {row.get('line_code', '')}"
            if row.get("line_code")
            else ""
        ): row["id"]
        for _, row in frame.iterrows()
    }
    if not choices:
        return None
    recent_choice = st.session_state.get(f"recent_{key or label}")
    options = list(choices)
    if recent_choice in options:
        options.remove(recent_choice)
        options.insert(0, recent_choice)
    selected = st.selectbox(label, options, key=key)
    st.session_state[f"recent_{key or label}"] = selected
    return choices[selected]


def show_previous(table_name: str, date_column: str, title: str = "Previous entries") -> None:
    previous = recent_rows(supabase, table_name, date_column, limit=5)
    if previous.empty:
        st.caption("No previous entries yet. Your first saved entry will become a suggestion.")
        return
    st.caption(title)
    visible = previous.drop(
        columns=[
            "id",
            "employee_id",
            "product_id",
            "material_id",
            "machine_id",
            "production_line_id",
            "shift_id",
        ],
        errors="ignore",
    )
    st.dataframe(visible, use_container_width=True, hide_index=True, height=190)


def save_entry(
    entry_type: str,
    target_table: str,
    payload: dict[str, Any],
    errors: list[str],
    direct_allowed: bool = False,
) -> None:
    if errors:
        for message in errors:
            st.error(message)
        return

    mode = st.radio(
        "Save workflow",
        ["Submit for supervisor review", "Save directly to operational table"],
        index=0,
        horizontal=True,
        key=f"save_mode_{entry_type}",
        help="Review is the normal operator workflow. Direct save is intended for an authorized manager.",
    )
    if mode == "Save directly to operational table":
        st.warning("Direct save writes official operational data immediately.")

    if not st.form_submit_button("Save entry", type="primary"):
        return

    try:
        if mode == "Submit for supervisor review":
            created = create_submission(
                supabase,
                entry_type,
                target_table,
                payload,
                actor_id,
            )
            write_audit(
                supabase,
                "submitted",
                "data_entry_submissions",
                created[0].get("id") if created else None,
                actor_id,
                {"entry_type": entry_type},
            )
            st.success("Entry submitted for supervisor review.")
        else:
            if not direct_allowed:
                st.error("Direct save is disabled for this form. Submit it for review.")
                return
            if target_table == "inventory_movements":
                record_id = apply_inventory_movement(supabase, payload)
                created = [{"id": record_id}] if record_id else []
            else:
                created = insert_record(supabase, target_table, payload)
            write_audit(
                supabase,
                "inserted",
                target_table,
                created[0].get("id") if created else None,
                actor_id,
                {"entry_type": entry_type},
            )
            st.success("Entry saved to the operational table.")
    except Exception as error:
        st.error(f"Could not save entry: {error}")


def production_form() -> None:
    st.header("Production entry")
    st.caption("Record one line-and-shift production result. Previous records guide the defaults.")
    lines = fetch_table(supabase, "production_lines")
    products = fetch_table(supabase, "products")
    shifts = fetch_table(supabase, "shifts")
    show_previous("production_records", "production_date")
    with st.form("production_entry"):
        left, right = st.columns(2)
        with left:
            production_date = st.date_input("Production date", value=date.today())
            line_id = select_lookup("Production line", lines, ["name"], "entry_line")
            product_id = select_lookup("Product", products, ["name"], "entry_product")
            shift_id = select_lookup("Shift", shifts, ["name"], "entry_shift")
        with right:
            planned = st.number_input("Planned quantity", min_value=0.0, step=1.0)
            actual = st.number_input("Actual quantity", min_value=0.0, step=1.0)
            rejected = st.number_input("Rejected quantity", min_value=0.0, step=1.0)
            downtime = st.number_input("Downtime (minutes)", min_value=0.0, step=1.0)
            reason = st.text_input("Downtime or delay reason")
        payload = {
            "production_date": production_date.isoformat(),
            "production_line_id": line_id,
            "product_id": product_id,
            "shift_id": shift_id,
            "planned_quantity": planned,
            "actual_quantity": actual,
            "rejected_quantity": rejected,
            "downtime_minutes": downtime,
            "downtime_reason": reason or None,
            "status": "completed",
        }
        errors = validate_required(
            payload,
            {
                "production_line_id": "Select a production line.",
                "product_id": "Select a product.",
                "shift_id": "Select a shift.",
            },
        ) + validate_production(payload)
        save_entry("production", "production_records", payload, errors, direct_allowed=True)


def inventory_form() -> None:
    st.header("Inventory movement")
    st.caption("Record receipts, consumption, transfers, or approved adjustments.")
    materials = fetch_table(supabase, "materials")
    show_previous("inventory_movements", "movement_date")
    with st.form("inventory_entry"):
        material_id = select_lookup("Material", materials, ["name"], "entry_material")
        movement_type = st.selectbox(
            "Movement type",
            ["receipt", "consumption", "transfer", "adjustment"],
        )
        quantity = st.number_input("Quantity", min_value=0.0, step=1.0)
        movement_date = st.date_input("Movement date", value=date.today())
        warehouse_location = st.text_input("Warehouse location", value="Main warehouse")
        reference = st.text_input("Reference or note")
        payload = {
            "material_id": material_id,
            "movement_type": movement_type,
            "quantity": quantity,
            "movement_date": movement_date.isoformat(),
            "warehouse_location": warehouse_location,
            "reference": reference or None,
            "recorded_by": actor_id,
        }
        errors = validate_required(payload, {"material_id": "Select a material."})
        if quantity <= 0:
            errors.append("Quantity must be greater than zero.")
        save_entry("inventory movement", "inventory_movements", payload, errors, direct_allowed=True)


def maintenance_form() -> None:
    st.header("Maintenance issue")
    machines = fetch_table(supabase, "machines")
    show_previous("maintenance_records", "reported_at")
    with st.form("maintenance_entry"):
        machine_id = select_lookup("Machine", machines, ["name"], "entry_machine")
        issue_type = st.selectbox(
            "Issue type",
            ["Breakdown", "Preventive maintenance", "Inspection", "Adjustment", "Other"],
        )
        description = st.text_area("Description")
        downtime = st.number_input("Downtime (minutes)", min_value=0.0, step=1.0)
        payload = {
            "machine_id": machine_id,
            "issue_type": issue_type,
            "description": description,
            "downtime_minutes": downtime,
            "status": "open",
            "reported_by": actor_id,
        }
        errors = validate_required(
            payload,
            {"machine_id": "Select a machine.", "description": "Enter a description."},
        )
        save_entry("maintenance", "maintenance_records", payload, errors, direct_allowed=True)


def quality_form() -> None:
    st.header("Quality inspection")
    records = recent_rows(supabase, "production_records", "production_date", limit=100)
    show_previous("quality_inspections", "inspection_date")
    with st.form("quality_entry"):
        production_record_id = select_lookup(
            "Production record",
            records,
            ["production_code", "production_date"],
            "entry_production_record",
        )
        inspected = st.number_input("Inspected quantity", min_value=0.0, step=1.0)
        rejected = st.number_input("Rejected quantity", min_value=0.0, step=1.0)
        defect_type = st.selectbox(
            "Defect type",
            ["None", "Color variation", "Dimension", "Strength", "Surface", "Packaging", "Other"],
        )
        notes = st.text_area("Inspection notes")
        payload = {
            "production_record_id": production_record_id,
            "inspected_quantity": inspected,
            "rejected_quantity": rejected,
            "defect_type": defect_type,
            "notes": notes or None,
            "inspection_date": date.today().isoformat(),
            "inspected_by": actor_id,
        }
        errors = validate_required(
            payload,
            {"production_record_id": "Select a production record."},
        )
        if rejected > inspected:
            errors.append("Rejected quantity cannot exceed inspected quantity.")
        save_entry("quality inspection", "quality_inspections", payload, errors, direct_allowed=True)


def attendance_form() -> None:
    st.header("Attendance and overtime")
    employees = fetch_table(supabase, "employees")
    shifts = fetch_table(supabase, "shifts")
    show_previous("employee_attendance", "attendance_date")
    with st.form("attendance_entry"):
        employee_id = select_lookup("Employee", employees, ["full_name"], "entry_employee")
        attendance_date = st.date_input("Attendance date", value=date.today())
        status = st.selectbox("Status", ["present", "absent", "leave", "late"])
        shift_id = select_lookup("Shift", shifts, ["name"], "attendance_shift")
        overtime_hours = st.number_input("Overtime hours", min_value=0.0, step=0.5)
        payload = {
            "employee_id": employee_id,
            "attendance_date": attendance_date,
            "status": status,
            "shift_id": shift_id,
            "overtime_hours": overtime_hours,
        }
        errors = validate_required(payload, {"employee_id": "Select an employee."})
        errors += validate_attendance(payload)
        payload["attendance_date"] = attendance_date.isoformat()
        save_entry("attendance", "employee_attendance", payload, errors, direct_allowed=True)


def shipment_form() -> None:
    st.header("Shipment update")
    shipments = recent_rows(supabase, "shipments", "expected_delivery_date", limit=100)
    if shipments.empty:
        st.info("No shipments are available.")
        return
    with st.form("shipment_entry"):
        shipment_id = select_lookup(
            "Shipment",
            shipments,
            ["shipment_code", "status"],
            "entry_shipment",
        )
        status = st.selectbox("New status", ["pending", "dispatched", "in transit", "delivered", "delayed"])
        actual_delivery_date = st.date_input("Actual delivery date", value=date.today())
        notes = st.text_input("Update note")
        if not st.form_submit_button("Submit shipment update", type="primary"):
            return
        if not shipment_id:
            st.error("Select a shipment.")
            return
        payload = {
            "shipment_id": shipment_id,
            "status": status,
            "actual_delivery_date": actual_delivery_date.isoformat()
            if status == "delivered"
            else None,
            "note": notes or None,
            "updated_by": actor_id,
        }
        try:
            created = create_submission(
                supabase,
                "shipment update",
                "shipments",
                payload,
                actor_id,
            )
            write_audit(
                supabase,
                "submitted",
                "data_entry_submissions",
                created[0].get("id") if created else None,
                actor_id,
                {"entry_type": "shipment update"},
            )
            st.success("Shipment update submitted for review.")
        except Exception as error:
            st.error(f"Could not submit update: {error}")


def review_queue() -> None:
    st.header("Submission queue")
    st.caption(f"Signed in as {actor_email}. Review or monitor submitted entries.")
    submissions = recent_rows(supabase, "data_entry_submissions", "submitted_at", limit=100)
    if submissions.empty:
        st.info("No submissions are waiting in the queue.")
        return
    status = st.selectbox("Status filter", ["All", "submitted", "approved", "rejected"])
    view = submissions if status == "All" else submissions[submissions["status"] == status]
    st.dataframe(
        view.drop(columns=["payload"], errors="ignore"),
        use_container_width=True,
        hide_index=True,
    )
    st.info(
        "Approval execution is intentionally separated from operator entry. Use the manager role or a controlled Supabase workflow to approve submissions."
    )


st.sidebar.title("FactoryOps")
st.sidebar.caption("Smart Data Entry")
if st.sidebar.button("Log out"):
    supabase.auth.sign_out()
    st.session_state.clear()
    st.rerun()

page = st.sidebar.radio(
    "Entry module",
    [
        "🏭 Production",
        "📦 Inventory",
        "⚙️ Maintenance",
        "✅ Quality",
        "👥 Attendance",
        "🚚 Shipments",
        "📋 Submission Queue",
    ],
)

try:
    if page == "🏭 Production":
        production_form()
    elif page == "📦 Inventory":
        inventory_form()
    elif page == "⚙️ Maintenance":
        maintenance_form()
    elif page == "✅ Quality":
        quality_form()
    elif page == "👥 Attendance":
        attendance_form()
    elif page == "🚚 Shipments":
        shipment_form()
    else:
        review_queue()
except Exception as error:
    st.error(f"This entry module could not load: {error}")
