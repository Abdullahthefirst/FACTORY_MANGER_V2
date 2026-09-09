"""Manager reports, calculated alerts, and downloadable operational summaries."""

from __future__ import annotations

from datetime import date
from typing import Callable

import pandas as pd
import streamlit as st

from src.database.updates import apply_submission


def _load(loader: Callable[[str], pd.DataFrame], table: str) -> pd.DataFrame:
    try:
        return loader(table)
    except Exception:
        return pd.DataFrame()


def _alerts(loader: Callable[[str], pd.DataFrame]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    today = pd.Timestamp(date.today())
    orders = _load(loader, "customer_orders")
    if not orders.empty and "due_date" in orders.columns:
        orders["due_date"] = pd.to_datetime(orders["due_date"], errors="coerce")
        for _, row in orders.iterrows():
            due = row.get("due_date")
            if str(row.get("status", "")).lower() == "delayed" or (pd.notna(due) and due < today):
                rows.append({"severity": "High", "area": "Orders", "title": f"Order {row.get('order_code', '')} is late", "detail": f"Due {due.date().isoformat() if pd.notna(due) else 'unknown'}"})

    inventory = _load(loader, "inventory")
    materials = _load(loader, "materials")
    if not inventory.empty and not materials.empty and {"material_id", "quantity"}.issubset(inventory.columns):
        fields = [c for c in ["id", "name", "material_code", "reorder_level"] if c in materials.columns]
        stock = inventory.merge(materials[fields], left_on="material_id", right_on="id", how="left")
        stock["quantity"] = pd.to_numeric(stock["quantity"], errors="coerce").fillna(0)
        stock["reorder_level"] = pd.to_numeric(stock.get("reorder_level", 0), errors="coerce").fillna(0)
        for _, row in stock[stock["quantity"] <= stock["reorder_level"]].iterrows():
            rows.append({"severity": "Critical" if row["quantity"] <= 0 else "High", "area": "Inventory", "title": f"{row.get('name', row.get('material_code', 'Material'))} below reorder level", "detail": f"Available {row['quantity']:,.0}; reorder at {row['reorder_level']:,.0}"})

    machines = _load(loader, "machines")
    if not machines.empty and "status" in machines.columns:
        for _, row in machines[machines["status"].astype(str).str.lower().isin(["down", "broken", "maintenance"])].iterrows():
            rows.append({"severity": "Critical", "area": "Maintenance", "title": f"Machine {row.get('machine_code', row.get('name', ''))} needs attention", "detail": f"Current status: {row.get('status', '')}"})

    quality = _load(loader, "quality_inspections")
    if not quality.empty and {"inspected_quantity", "rejected_quantity"}.issubset(quality.columns):
        inspected = pd.to_numeric(quality["inspected_quantity"], errors="coerce").fillna(0)
        rejected = pd.to_numeric(quality["rejected_quantity"], errors="coerce").fillna(0)
        for _, row in quality[inspected.gt(0) & rejected.div(inspected).gt(0.05)].iterrows():
            rows.append({"severity": "High", "area": "Quality", "title": f"High defect rate: {row.get('defect_type', 'Unspecified')}", "detail": "Inspection rejection rate is above 5%."})

    safety = _load(loader, "safety_incidents")
    if not safety.empty and "status" in safety.columns:
        for _, row in safety[safety["status"].astype(str).str.lower().isin(["open", "investigating"])].iterrows():
            rows.append({"severity": str(row.get("severity", "medium")).title(), "area": "Safety", "title": f"Open {row.get('incident_type', 'safety incident')}", "detail": str(row.get("description", "Investigation required."))})

    result = pd.DataFrame(rows, columns=["severity", "area", "title", "detail"])
    if not result.empty:
        severity_order = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
        result["_order"] = result["severity"].map(severity_order).fillna(9)
        result = result.sort_values(["_order", "area"]).drop(columns="_order")
    return result


def render_reports_page(loader: Callable[[str], pd.DataFrame], table_renderer: Callable[..., None], client=None, reviewer_id: str | None = None) -> None:
    st.title("Reports & Alerts")
    st.caption("Operational exceptions, trends, and exportable management reports.")
    alerts = _alerts(loader)
    tab_alerts, tab_production, tab_costs, tab_export, tab_queue = st.tabs(["Live Alerts", "Production Report", "Cost Report", "Export", "Review Queue"])
    with tab_alerts:
        if alerts.empty:
            st.success("No calculated alerts require attention.")
        else:
            st.metric("Open calculated alerts", len(alerts))
            table_renderer(alerts, ["severity", "area", "title", "detail"], show_all_fields=False)
    with tab_production:
        production = _load(loader, "production_records")
        if production.empty:
            st.info("No production records available for a report.")
        else:
            production["production_date"] = pd.to_datetime(production["production_date"], errors="coerce")
            for column in ["planned_quantity", "actual_quantity"]:
                production[column] = pd.to_numeric(production[column], errors="coerce").fillna(0)
            report = production.groupby("production_date", as_index=False)[["planned_quantity", "actual_quantity"]].sum()
            report["efficiency_percent"] = report["actual_quantity"].div(report["planned_quantity"].replace(0, pd.NA)).mul(100).fillna(0).round(1)
            st.line_chart(report.set_index("production_date")[["planned_quantity", "actual_quantity"]])
            table_renderer(report, ["production_date", "planned_quantity", "actual_quantity", "efficiency_percent"], show_all_fields=False)
    with tab_costs:
        costs = _load(loader, "operating_costs")
        if costs.empty:
            st.info("No operating costs available for a report.")
        else:
            costs["amount"] = pd.to_numeric(costs["amount"], errors="coerce").fillna(0)
            summary = costs.groupby("category", as_index=False)["amount"].sum().sort_values("amount", ascending=False)
            st.bar_chart(summary.set_index("category"))
            table_renderer(summary, ["category", "amount"], show_all_fields=False)
    with tab_export:
        datasets = ["production_records", "customer_orders", "inventory", "maintenance_records", "quality_inspections", "employee_attendance", "shipments", "operating_costs", "safety_incidents"]
        selected = st.selectbox("Report dataset", datasets)
        data = _load(loader, selected)
        if data.empty:
            st.info("This dataset is empty.")
        else:
            st.download_button("Download CSV", data.to_csv(index=False).encode("utf-8"), file_name=f"factoryops_{selected}_{date.today().isoformat()}.csv", mime="text/csv")
    with tab_queue:
        submissions = _load(loader, "data_entry_submissions")
        if submissions.empty:
            st.info("No data-entry submissions are waiting for review.")
        else:
            pending = submissions[submissions.get("status", "").astype(str).str.lower() == "submitted"] if "status" in submissions.columns else submissions
            if pending.empty:
                st.success("The review queue is clear.")
            else:
                st.write(f"{len(pending)} submission(s) awaiting review.")
                st.dataframe(pending.drop(columns=["payload"], errors="ignore"), use_container_width=True, hide_index=True)
                if client is None or not reviewer_id:
                    st.info("Review actions are unavailable until the manager client is connected.")
                else:
                    for _, row in pending.iterrows():
                        submission_id = str(row.get("id", ""))
                        with st.expander(f"{row.get('submission_code', submission_id)} · {row.get('entry_type', 'Entry')}"):
                            st.json(row.get("payload", {}))
                            note = st.text_input("Review note", key=f"review_note_{submission_id}")
                            approve_col, reject_col = st.columns(2)
                            if approve_col.button("Approve and apply", key=f"approve_{submission_id}", type="primary"):
                                try:
                                    apply_submission(client, submission_id, reviewer_id, True, note)
                                    st.success("Approved and applied. Refresh the page to update the queue.")
                                except Exception as error:
                                    st.error(f"Approval failed: {error}")
                            if reject_col.button("Reject", key=f"reject_{submission_id}"):
                                try:
                                    apply_submission(client, submission_id, reviewer_id, False, note)
                                    st.warning("Submission rejected. Refresh the page to update the queue.")
                                except Exception as error:
                                    st.error(f"Rejection failed: {error}")
