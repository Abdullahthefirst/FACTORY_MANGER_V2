"""Streamlit application entry point."""

import altair as alt
import pandas as pd
import streamlit as st
from supabase import create_client

from src.ai.ui import (
    init_ai_state,
    render_ai_page,
    render_dashboard_ai_suggestions,
)


st.set_page_config(page_title="FactoryOps", layout="wide")

st.markdown(
    """
    <style>
        .block-container {
            padding-top: 2rem;
            padding-bottom: 3rem;
        }

        [data-testid="stMetric"] {
            background-color: #f7f9fc;
            border: 1px solid #e3e8ef;
            border-radius: 12px;
            padding: 16px;
            box-shadow: 0 2px 6px rgba(0, 0, 0, 0.04);
        }

        [data-testid="stMetricLabel"] {
            color: #64748b;
            font-size: 0.85rem;
        }

        [data-testid="stMetricValue"] {
            color: #17324d;
            font-size: 1.8rem;
            font-weight: 700;
        }

        h1, h2, h3 {
            color: #17324d;
        }

        [data-testid="stSidebar"] {
            background-color: #f8fafc;
        }

        [data-testid="stSidebar"] h1 {
            color: #17324d;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# Configure these values in Streamlit Cloud -> App -> Settings -> Secrets.
# Use only the publishable Supabase key; never use a database password or
# service-role key in Streamlit Cloud.
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

if "access_token" in st.session_state:
    try:
        supabase.auth.set_session(
            st.session_state["access_token"],
            st.session_state["refresh_token"],
        )
    except Exception:
        st.session_state.clear()
        st.rerun()

if "user" not in st.session_state:
    st.session_state.user = None

if st.session_state.user is None:
    st.title("FactoryOps Login")

    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Log in"):
        try:
            response = supabase.auth.sign_in_with_password(
                {"email": email, "password": password}
            )
            st.session_state.user = response.user
            st.session_state.access_token = response.session.access_token
            st.session_state.refresh_token = response.session.refresh_token
            st.success("Login successful.")
            st.rerun()
        except Exception as error:
            st.error(f"Login failed: {error}")

    st.stop()

init_ai_state()

st.sidebar.title("FactoryOps")
st.sidebar.caption("Manager Control Center")

if st.sidebar.button("Log out"):
    supabase.auth.sign_out()
    st.session_state.user = None
    st.session_state.pop("access_token", None)
    st.session_state.pop("refresh_token", None)
    st.rerun()


page = st.sidebar.radio(
    "Navigate",
    [
        "📊 Overview",
        "🤖 AI Center",
        "📦 Orders & Demand",
        "🏭 Production",
        "📦 Inventory & Supply",
        "⚙️ Machines & Maintenance",
        "✅ Quality",
        "👥 Workforce",
        "🚚 Logistics",
        "💰 Costs",
        "🛡️ Safety & Risk",
    ],
)


def load_table(table_name: str) -> pd.DataFrame:
    """Load a Supabase table into a DataFrame for the selected module."""
    response = supabase.table(table_name).select("*").execute()
    return pd.DataFrame(response.data)


def add_lookup_name(
    df: pd.DataFrame,
    lookup_df: pd.DataFrame,
    source_column: str,
    output_column: str,
    lookup_name_column: str = "name",
) -> pd.DataFrame:
    """Attach a readable lookup name while retaining the internal UUID key."""
    if df.empty or lookup_df.empty:
        return df

    lookup = lookup_df[["id", lookup_name_column]].rename(
        columns={
            "id": f"{source_column}_lookup",
            lookup_name_column: output_column,
        }
    )
    return df.merge(
        lookup,
        left_on=source_column,
        right_on=f"{source_column}_lookup",
        how="left",
    )


def manager_view(df: pd.DataFrame) -> pd.DataFrame:
    """Hide database identifiers from manager-facing tables."""
    hidden_columns = [
        "id",
        "department_id",
        "employee_id",
        "product_id",
        "material_id",
        "supplier_id",
        "machine_id",
        "production_line_id",
        "shift_id",
        "order_id",
        "production_record_id",
        "production_line_id_lookup",
        "product_id_lookup",
        "shift_id_lookup",
        "material_id_lookup",
        "supplier_id_lookup",
        "machine_id_lookup",
        "id_material",
        "id_x",
        "id_y",
    ]
    lookup_columns = [
        column for column in df.columns
        if column.endswith("_lookup")
    ]
    return df.drop(
        columns=hidden_columns + lookup_columns,
        errors="ignore",
    )


def arrange_columns(
    df: pd.DataFrame,
    preferred_columns: list[str],
    include_remaining: bool = False,
) -> pd.DataFrame:
    """Select manager-first fields, optionally followed by all others."""
    selected = [
        column for column in preferred_columns
        if column in df.columns
    ]

    if not include_remaining:
        return df[selected]

    remaining = [
        column for column in df.columns
        if column not in selected
    ]
    return df[selected + remaining]


def style_status(value: object) -> str:
    """Apply manager-friendly status colors to dataframe cells."""
    value = str(value).lower()

    if value in [
        "operational",
        "completed",
        "approved",
        "present",
        "received",
        "healthy",
        "normal",
    ]:
        return "color: #15803d; font-weight: 600"

    if value in [
        "pending",
        "in progress",
        "ordered",
        "planned",
        "attention",
        "medium",
    ]:
        return "color: #b45309; font-weight: 600"

    if value in [
        "delayed",
        "open",
        "maintenance",
        "absent",
        "rejected",
        "critical",
        "high",
        "low stock",
    ]:
        return "color: #dc2626; font-weight: 600"

    return ""


def render_manager_table(
    df: pd.DataFrame,
    preferred_columns: list[str],
    show_all_fields: bool = True,
) -> None:
    """Render a manager-first table with an optional full-field view."""

    readable_names = {
        "status": "Status",
        "priority": "Priority",
        "severity": "Severity",
        "production_code": "Production Code",
        "production_date": "Production Date",
        "production_line_name": "Production Line",
        "product_name": "Product",
        "shift_name": "Shift",
        "planned_quantity": "Planned Quantity",
        "actual_quantity": "Actual Quantity",
        "rejected_quantity": "Rejected Quantity",
        "downtime_minutes": "Downtime",
        "stock_status": "Stock Status",
        "material_code": "Material Code",
        "material_name": "Material",
        "quantity": "Quantity",
        "unit": "Unit",
        "reorder_level": "Reorder Level",
        "reorder_gap": "Reorder Gap",
        "supplier_name": "Supplier",
        "purchase_order_code": "Purchase Order",
        "ordered_quantity": "Ordered Quantity",
        "received_quantity": "Received Quantity",
        "expected_date": "Expected Date",
        "machine_code": "Machine Code",
        "machine_name": "Machine",
        "total_downtime": "Total Downtime",
        "open_issues": "Open Issues",
        "maintenance_events": "Maintenance Events",
        "maintenance_code": "Maintenance Code",
        "issue_type": "Issue Type",
        "defect_type": "Defect Type",
        "defect_rate": "Defect Rate",
        "inspection_date": "Inspection Date",
        "employee_code": "Employee Code",
        "full_name": "Employee",
        "attendance_date": "Attendance Date",
        "overtime_hours": "Overtime Hours",
        "incident_code": "Incident Code",
        "incident_date": "Incident Date",
        "incident_type": "Incident Type",
        "cost_date": "Cost Date",
        "category": "Category",
        "amount": "Amount",
        "description": "Description",
    }

    date_columns = [
        "production_date",
        "due_date",
        "order_date",
        "expected_date",
        "cost_date",
        "incident_date",
        "attendance_date",
    ]
    integer_columns = [
        "quantity",
        "planned_quantity",
        "actual_quantity",
        "rejected_quantity",
        "downtime_minutes",
        "total_downtime",
        "reorder_level",
        "reorder_gap",
        "ordered_quantity",
        "received_quantity",
        "open_issues",
        "maintenance_events",
    ]

    def format_for_display(table_df: pd.DataFrame):
        table_df = table_df.copy()

        for column in date_columns:
            if column in table_df.columns:
                table_df[column] = pd.to_datetime(
                    table_df[column],
                    errors="coerce",
                ).dt.strftime("%Y-%m-%d")

        for column in integer_columns:
            if column in table_df.columns:
                table_df[column] = pd.to_numeric(
                    table_df[column],
                    errors="coerce",
                ).fillna(0).map(lambda value: f"{value:,.0f}")

        table_df = table_df.rename(columns=readable_names)
        styled_df = table_df.style

        for column in ["Status", "Priority", "Severity", "Stock Status"]:
            if column in table_df.columns:
                styled_df = styled_df.map(style_status, subset=[column])

        return styled_df

    manager_df = arrange_columns(
        manager_view(df).copy(),
        preferred_columns,
        include_remaining=False,
    )
    st.dataframe(
        format_for_display(manager_df),
        use_container_width=True,
        hide_index=True,
        height=400,
    )

    if show_all_fields:
        with st.expander("View all fields"):
            all_fields_df = arrange_columns(
                manager_view(df).copy(),
                preferred_columns,
                include_remaining=True,
            )
            st.dataframe(
                format_for_display(all_fields_df),
                use_container_width=True,
                hide_index=True,
                height=400,
            )


try:
    if page == "📊 Overview":
        st.title("Factory Overview")
        st.caption("Manager-level summary of today's factory performance.")

        production_df = load_table("production_records")
        orders_df = load_table("customer_orders")
        machines_df = load_table("machines")
        quality_df = load_table("quality_inspections")
        safety_df = load_table("safety_incidents")
        inventory_df = load_table("inventory")
        materials_df = load_table("materials")

        actual_production = 0
        planned_production = 0
        production_efficiency = 0

        if not production_df.empty:
            production_df["actual_quantity"] = pd.to_numeric(
                production_df["actual_quantity"],
                errors="coerce",
            ).fillna(0)
            production_df["planned_quantity"] = pd.to_numeric(
                production_df["planned_quantity"],
                errors="coerce",
            ).fillna(0)
            actual_production = production_df["actual_quantity"].sum()
            planned_production = production_df["planned_quantity"].sum()

            if planned_production > 0:
                production_efficiency = (
                    actual_production / planned_production * 100
                )

        active_orders = 0
        delayed_orders = 0

        if not orders_df.empty:
            order_status = orders_df["status"].astype(str).str.lower()
            active_orders = order_status.isin(["pending", "in production"]).sum()
            delayed_orders = (order_status == "delayed").sum()

        machine_issues = 0

        if not machines_df.empty:
            machine_issues = (
                machines_df["status"].astype(str).str.lower().ne("operational").sum()
            )

        open_safety = 0

        if not safety_df.empty:
            open_safety = (
                safety_df["status"].astype(str).str.lower().eq("open").sum()
            )

        low_stock = 0

        if not inventory_df.empty and not materials_df.empty:
            inventory_check = inventory_df.merge(
                materials_df[["id", "reorder_level"]],
                left_on="material_id",
                right_on="id",
                how="left",
            )
            inventory_check["quantity"] = pd.to_numeric(
                inventory_check["quantity"],
                errors="coerce",
            ).fillna(0)
            inventory_check["reorder_level"] = pd.to_numeric(
                inventory_check["reorder_level"],
                errors="coerce",
            ).fillna(0)
            low_stock = (
                inventory_check["quantity"] <= inventory_check["reorder_level"]
            ).sum()

        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Production Efficiency", f"{production_efficiency:.1f}%")
        col2.metric("Active Orders", active_orders)
        col3.metric("Delayed Orders", delayed_orders)
        col4.metric("Low-Stock Materials", low_stock)
        col5.metric("Machine Issues", machine_issues)

        st.subheader("Factory Attention Summary")
        summary_df = pd.DataFrame(
            {
                "Area": ["Production", "Orders", "Inventory", "Machines", "Safety"],
                "Status": [
                    "On Track" if production_efficiency >= 90 else "Below Target",
                    "Delayed" if delayed_orders > 0 else "On Track",
                    "Low Stock" if low_stock > 0 else "Healthy",
                    "Attention Required" if machine_issues > 0 else "Operational",
                    "Open Incidents" if open_safety > 0 else "Clear",
                ],
                "Count": [
                    f"{actual_production:,.0f} units produced",
                    f"{delayed_orders} delayed",
                    f"{low_stock} below reorder level",
                    f"{machine_issues} needing attention",
                    f"{open_safety} open incidents",
                ],
            }
        )

        render_manager_table(summary_df, ["Status", "Area", "Count"])
        render_dashboard_ai_suggestions()

    elif page == "🤖 AI Center":
        render_ai_page(load_table)

    elif page == "📦 Orders & Demand":
        st.title("Orders & Demand")
        st.caption("Monitor delivery commitments and identify orders at risk.")

        orders_df = load_table("customer_orders")
        products_df = load_table("products")
        orders_df = add_lookup_name(
            orders_df,
            products_df,
            "product_id",
            "product_name",
        )

        if orders_df.empty:
            st.info("No customer orders available.")
        else:
            orders_df["due_date"] = pd.to_datetime(
                orders_df["due_date"],
                errors="coerce",
            )

            today = pd.Timestamp.now().normalize()
            orders_df["days_remaining"] = (
                orders_df["due_date"] - today
            ).dt.days

            def calculate_risk(row: pd.Series) -> str:
                status = str(row.get("status", "")).lower()
                days = row.get("days_remaining")

                if status == "delayed":
                    return "Critical"

                if pd.notna(days) and days < 0:
                    return "Critical"

                if pd.notna(days) and days <= 3:
                    return "At Risk"

                if str(row.get("priority", "")).lower() == "urgent":
                    return "At Risk"

                return "Normal"

            orders_df["risk"] = orders_df.apply(calculate_risk, axis=1)

            priority_options = ["All"] + sorted(
                orders_df["priority"].dropna().astype(str).unique().tolist()
            )
            selected_priority = st.selectbox("Priority", priority_options)

            filtered_orders = orders_df.copy()

            if selected_priority != "All":
                filtered_orders = filtered_orders[
                    filtered_orders["priority"].astype(str) == selected_priority
                ]

            total_orders = len(filtered_orders)
            at_risk_orders = len(
                filtered_orders[
                    filtered_orders["risk"].isin(["Critical", "At Risk"])
                ]
            )
            delayed_orders = len(
                filtered_orders[
                    filtered_orders["status"].astype(str).str.lower()
                    == "delayed"
                ]
            )
            total_quantity = pd.to_numeric(
                filtered_orders["quantity"],
                errors="coerce",
            ).fillna(0).sum()

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total Orders", total_orders)
            col2.metric("Orders at Risk", at_risk_orders)
            col3.metric("Delayed Orders", delayed_orders)
            col4.metric("Committed Quantity", f"{total_quantity:,.0f}")

            st.subheader("Order Risk Monitor")
            render_manager_table(
                filtered_orders,
                [
                    "risk",
                    "status",
                    "priority",
                    "order_code",
                    "customer_name",
                    "product_name",
                    "due_date",
                    "quantity",
                    "days_remaining",
                ],
            )

    elif page == "🏭 Production":
        st.title("Production Monitoring")
        production_df = load_table("production_records")
        lines_df = load_table("production_lines")
        products_df = load_table("products")
        shifts_df = load_table("shifts")
        production_df = add_lookup_name(
            production_df,
            lines_df,
            "production_line_id",
            "production_line_name",
        )
        production_df = add_lookup_name(
            production_df,
            products_df,
            "product_id",
            "product_name",
        )
        production_df = add_lookup_name(
            production_df,
            shifts_df,
            "shift_id",
            "shift_name",
        )

        if production_df.empty:
            st.info("No production records available.")
        else:
            production_df["production_date"] = pd.to_datetime(
                production_df["production_date"]
            )

            min_date = production_df["production_date"].min().date()
            max_date = production_df["production_date"].max().date()

            selected_dates = st.date_input(
                "Production date range",
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date,
            )

            if isinstance(selected_dates, tuple) and len(selected_dates) == 2:
                start_date, end_date = selected_dates
                filtered_df = production_df[
                    (production_df["production_date"].dt.date >= start_date)
                    & (production_df["production_date"].dt.date <= end_date)
                ]
            else:
                filtered_df = production_df

            planned = filtered_df["planned_quantity"].sum()
            actual = filtered_df["actual_quantity"].sum()
            rejected = filtered_df["rejected_quantity"].sum()
            downtime = filtered_df["downtime_minutes"].sum()

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Planned", f"{planned:,.0f}")
            col2.metric("Actual", f"{actual:,.0f}")
            col3.metric("Rejected", f"{rejected:,.0f}")
            col4.metric("Downtime", f"{downtime:,.0f} min")

            chart_data = (
                filtered_df[
                    ["production_date", "planned_quantity", "actual_quantity"]
                ]
                .groupby("production_date", as_index=False)[
                    ["planned_quantity", "actual_quantity"]
                ]
                .sum()
            )

            chart_data["production_date"] = pd.to_datetime(
                chart_data["production_date"]
            )

            origin_date = (
                chart_data["production_date"].min()
                - pd.Timedelta(days=1)
            )
            origin_row = pd.DataFrame(
                {
                    "production_date": [origin_date],
                    "planned_quantity": [0],
                    "actual_quantity": [0],
                }
            )

            chart_data = pd.concat(
                [origin_row, chart_data],
                ignore_index=True,
            ).sort_values("production_date")

            chart_data = chart_data.melt(
                id_vars=["production_date"],
                value_vars=["planned_quantity", "actual_quantity"],
                var_name="Metric",
                value_name="Quantity",
            )

            chart_data["Metric"] = chart_data["Metric"].replace(
                {
                    "actual_quantity": "Actual Production",
                    "planned_quantity": "Planned Production",
                }
            )

            production_chart = (
                alt.Chart(chart_data)
                .mark_line(point=True, strokeWidth=3)
                .encode(
                    x=alt.X(
                        "production_date:T",
                        title="Production Date",
                        axis=alt.Axis(format="%b %d", labelAngle=-45),
                    ),
                    y=alt.Y(
                        "Quantity:Q",
                        title="Units",
                        scale=alt.Scale(zero=True),
                    ),
                    color=alt.Color(
                        "Metric:N",
                        title=None,
                        scale=alt.Scale(
                            domain=["Actual Production", "Planned Production"],
                            range=["#1769aa", "#8ecae6"],
                        ),
                    ),
                    tooltip=[
                        alt.Tooltip(
                            "production_date:T",
                            title="Date",
                            format="%Y-%m-%d",
                        ),
                        alt.Tooltip("Metric:N"),
                        alt.Tooltip(
                            "Quantity:Q",
                            title="Units",
                            format=",.0f",
                        ),
                    ],
                )
                .properties(height=380, title="Planned vs Actual Production")
                .interactive()
            )

            st.subheader("Production Performance")
            st.altair_chart(
                production_chart,
                use_container_width=True,
            )

            st.subheader("Production Records")
            render_manager_table(
                filtered_df,
                [
                    "status",
                    "production_code",
                    "production_date",
                    "production_line_name",
                    "product_name",
                    "shift_name",
                    "planned_quantity",
                    "actual_quantity",
                    "rejected_quantity",
                    "downtime_minutes",
                ],
            )

    elif page == "📦 Inventory & Supply":
        st.title("Inventory & Supply")
        st.caption("Monitor stock levels, reorder risks, and supplier deliveries.")

        inventory_df = load_table("inventory")
        materials_df = load_table("materials")
        suppliers_df = load_table("suppliers")
        purchase_orders_df = load_table("purchase_orders")
        purchase_orders_df = add_lookup_name(
            purchase_orders_df,
            materials_df,
            "material_id",
            "material_name",
        )
        purchase_orders_df = add_lookup_name(
            purchase_orders_df,
            suppliers_df,
            "supplier_id",
            "supplier_name",
        )

        if inventory_df.empty:
            st.info("No inventory records available.")
        else:
            material_columns = [
                "id",
                "name",
                "material_code",
                "unit",
                "reorder_level",
                "supplier_id",
            ]
            inventory_view = inventory_df.merge(
                materials_df[material_columns],
                left_on="material_id",
                right_on="id",
                how="left",
                suffixes=("", "_material"),
            )

            supplier_columns = ["id", "name"]
            inventory_view = inventory_view.merge(
                suppliers_df[supplier_columns].rename(
                    columns={
                        "id": "supplier_id_lookup",
                        "name": "supplier_name",
                    }
                ),
                left_on="supplier_id",
                right_on="supplier_id_lookup",
                how="left",
            )
            inventory_view = inventory_view.rename(columns={"name": "material_name"})

            inventory_view["quantity"] = pd.to_numeric(
                inventory_view["quantity"],
                errors="coerce",
            ).fillna(0)
            inventory_view["reorder_level"] = pd.to_numeric(
                inventory_view["reorder_level"],
                errors="coerce",
            ).fillna(0)
            inventory_view["reorder_gap"] = (
                inventory_view["reorder_level"] - inventory_view["quantity"]
            ).clip(lower=0)
            inventory_view["stock_status"] = inventory_view.apply(
                lambda row: (
                    "Critical"
                    if row["quantity"] == 0
                    else "Low Stock"
                    if row["quantity"] <= row["reorder_level"]
                    else "Healthy"
                ),
                axis=1,
            )

            total_materials = len(inventory_view)
            low_stock_count = len(
                inventory_view[
                    inventory_view["stock_status"].isin(["Critical", "Low Stock"])
                ]
            )
            healthy_count = len(
                inventory_view[inventory_view["stock_status"] == "Healthy"]
            )

            col1, col2, col3 = st.columns(3)
            col1.metric("Materials Tracked", total_materials)
            col2.metric("Low-Stock Materials", low_stock_count)
            col3.metric("Healthy Materials", healthy_count)

            st.subheader("Inventory Status")

            stock_priority = {
                "Critical": 0,
                "Low Stock": 1,
                "Healthy": 2,
            }
            inventory_view["_status_priority"] = (
                inventory_view["stock_status"].map(stock_priority).fillna(99)
            )
            inventory_view = (
                inventory_view
                .sort_values(by=["_status_priority", "material_name"])
                .drop(columns=["_status_priority"])
            )

            render_manager_table(
                inventory_view,
                [
                    "stock_status",
                    "material_code",
                    "material_name",
                    "quantity",
                    "unit",
                    "reorder_level",
                    "reorder_gap",
                    "supplier_name",
                    "warehouse_location",
                ],
            )

        st.subheader("Purchase Orders")

        if purchase_orders_df.empty:
            st.info("No purchase orders available.")
        else:
            render_manager_table(
                purchase_orders_df,
                [
                    "status",
                    "purchase_order_code",
                    "material_name",
                    "supplier_name",
                    "ordered_quantity",
                    "received_quantity",
                    "expected_date",
                ],
            )

    elif page == "⚙️ Machines & Maintenance":
        st.title("Machines & Maintenance")
        st.caption("Monitor machine condition, downtime, and open maintenance work.")

        machines_df = load_table("machines")
        maintenance_df = load_table("maintenance_records")
        maintenance_df = add_lookup_name(
            maintenance_df,
            machines_df,
            "machine_id",
            "machine_name",
        )

        if machines_df.empty:
            st.info("No machine records available.")
        else:
            if not maintenance_df.empty:
                maintenance_df["downtime_minutes"] = pd.to_numeric(
                    maintenance_df["downtime_minutes"],
                    errors="coerce",
                ).fillna(0)

                maintenance_summary = (
                    maintenance_df
                    .groupby("machine_id", as_index=False)
                    .agg(
                        total_downtime=("downtime_minutes", "sum"),
                        maintenance_events=("id", "count"),
                        open_issues=(
                            "status",
                            lambda values: (
                                values.astype(str).str.lower().eq("open").sum()
                            ),
                        ),
                    )
                )

                machine_view = machines_df.merge(
                    maintenance_summary,
                    left_on="id",
                    right_on="machine_id",
                    how="left",
                )
            else:
                machine_view = machines_df.copy()
                machine_view["total_downtime"] = 0
                machine_view["maintenance_events"] = 0
                machine_view["open_issues"] = 0

            machine_view["total_downtime"] = machine_view[
                "total_downtime"
            ].fillna(0)
            machine_view["maintenance_events"] = machine_view[
                "maintenance_events"
            ].fillna(0)
            machine_view["open_issues"] = machine_view["open_issues"].fillna(0)

            def machine_priority(row: pd.Series) -> str:
                status = str(row.get("status", "")).lower()

                if status in ["broken", "down", "maintenance"]:
                    return "Critical"

                if row.get("open_issues", 0) > 0:
                    return "Attention"

                return "Operational"

            machine_view["priority"] = machine_view.apply(
                machine_priority,
                axis=1,
            )

            priority_order = {
                "Critical": 0,
                "Attention": 1,
                "Operational": 2,
            }
            machine_view["_priority_order"] = (
                machine_view["priority"].map(priority_order).fillna(99)
            )
            machine_view = (
                machine_view
                .sort_values(by=["_priority_order", "name"])
                .drop(columns=["_priority_order"])
            )

            critical_count = len(
                machine_view[machine_view["priority"] == "Critical"]
            )
            attention_count = len(
                machine_view[machine_view["priority"] == "Attention"]
            )
            total_downtime = machine_view["total_downtime"].sum()

            col1, col2, col3 = st.columns(3)
            col1.metric("Machines", len(machine_view))
            col2.metric("Critical Machines", critical_count)
            col3.metric("Total Downtime", f"{total_downtime:,.0f} min")

            st.subheader("Machine Status")
            render_manager_table(
                machine_view,
                [
                    "priority",
                    "status",
                    "machine_code",
                    "name",
                    "total_downtime",
                    "open_issues",
                    "maintenance_events",
                    "last_maintenance_date",
                ],
            )

            st.subheader("Maintenance Records")

            if maintenance_df.empty:
                st.info("No maintenance records available.")
            else:
                render_manager_table(
                    maintenance_df,
                    [
                        "status",
                        "maintenance_code",
                        "machine_name",
                        "issue_type",
                        "downtime_minutes",
                        "reported_at",
                        "resolved_at",
                    ],
                )

    elif page == "✅ Quality":
        st.title("Quality Management")
        st.caption("Monitor defects, rejected units, and quality risks.")

        quality_df = load_table("quality_inspections")

        if quality_df.empty:
            st.info("No quality inspection records available.")
        else:
            quality_df["inspected_quantity"] = pd.to_numeric(
                quality_df["inspected_quantity"],
                errors="coerce",
            ).fillna(0)
            quality_df["rejected_quantity"] = pd.to_numeric(
                quality_df["rejected_quantity"],
                errors="coerce",
            ).fillna(0)
            quality_df["defect_rate"] = 0.0

            valid_rows = quality_df["inspected_quantity"] > 0
            quality_df.loc[valid_rows, "defect_rate"] = (
                quality_df.loc[valid_rows, "rejected_quantity"]
                / quality_df.loc[valid_rows, "inspected_quantity"]
                * 100
            )

            def quality_priority(rate: float) -> str:
                if rate >= 5:
                    return "Critical"

                if rate >= 2:
                    return "Attention"

                return "Normal"

            quality_df["priority"] = quality_df["defect_rate"].apply(
                quality_priority
            )

            priority_order = {
                "Critical": 0,
                "Attention": 1,
                "Normal": 2,
            }
            quality_df["_priority_order"] = (
                quality_df["priority"].map(priority_order).fillna(99)
            )
            quality_df = (
                quality_df
                .sort_values(
                    by=["_priority_order", "defect_rate"],
                    ascending=[True, False],
                )
                .drop(columns=["_priority_order"])
            )

            total_inspected = quality_df["inspected_quantity"].sum()
            total_rejected = quality_df["rejected_quantity"].sum()
            overall_defect_rate = (
                total_rejected / total_inspected * 100
                if total_inspected > 0
                else 0
            )
            critical_count = len(
                quality_df[quality_df["priority"] == "Critical"]
            )

            col1, col2, col3 = st.columns(3)
            col1.metric("Inspected Units", f"{total_inspected:,.0f}")
            col2.metric("Rejected Units", f"{total_rejected:,.0f}")
            col3.metric("Overall Defect Rate", f"{overall_defect_rate:.2f}%")

            st.subheader("Quality Risk Monitor")
            render_manager_table(
                quality_df,
                [
                    "priority",
                    "defect_type",
                    "defect_rate",
                    "inspected_quantity",
                    "rejected_quantity",
                    "inspection_date",
                    "notes",
                ],
            )

            st.subheader("Defects by Type")
            defect_summary = (
                quality_df
                .groupby("defect_type", as_index=False)["rejected_quantity"]
                .sum()
                .sort_values("rejected_quantity", ascending=False)
            )
            st.bar_chart(
                defect_summary.set_index("defect_type"),
                height=300,
            )

    elif page == "👥 Workforce":
        st.title("Workforce Management")
        st.caption("Monitor attendance, staffing availability, and overtime.")

        employees_df = load_table("employees")
        attendance_df = load_table("employee_attendance")

        if employees_df.empty:
            st.info("No employee records available.")
        else:
            if attendance_df.empty:
                st.warning(
                    "Employee records exist, but no attendance has been entered."
                )
                render_manager_table(
                    employees_df,
                    [
                        "active",
                        "employee_code",
                        "full_name",
                        "role",
                        "skill_level",
                    ],
                )
            else:
                attendance_view = attendance_df.merge(
                    employees_df[
                        [
                            "id",
                            "employee_code",
                            "full_name",
                            "role",
                            "skill_level",
                            "department_id",
                        ]
                    ],
                    left_on="employee_id",
                    right_on="id",
                    how="left",
                )

                attendance_view["overtime_hours"] = pd.to_numeric(
                    attendance_view["overtime_hours"],
                    errors="coerce",
                ).fillna(0)

                status_order = {
                    "absent": 0,
                    "leave": 1,
                    "late": 2,
                    "present": 3,
                }
                attendance_view["_status_order"] = (
                    attendance_view["status"]
                    .astype(str)
                    .str.lower()
                    .map(status_order)
                    .fillna(99)
                )
                attendance_view = (
                    attendance_view
                    .sort_values(by=["_status_order", "full_name"])
                    .drop(columns=["_status_order"])
                )

                attendance_status = attendance_view["status"].astype(str).str.lower()
                present_count = (attendance_status == "present").sum()
                absent_count = (attendance_status == "absent").sum()
                leave_count = (attendance_status == "leave").sum()
                total_overtime = attendance_view["overtime_hours"].sum()

                col1, col2, col3, col4, col5 = st.columns(5)
                col1.metric("Employees", len(employees_df))
                col2.metric("Present", present_count)
                col3.metric("Absent", absent_count)
                col4.metric("On Leave", leave_count)
                col5.metric("Overtime Hours", f"{total_overtime:,.1f}")

                st.subheader("Attendance Overview")
                render_manager_table(
                    attendance_view,
                    [
                        "status",
                        "employee_code",
                        "full_name",
                        "role",
                        "attendance_date",
                        "shift_id",
                        "overtime_hours",
                    ],
                )

    elif page == "🚚 Logistics":
        st.title("Logistics")
        render_manager_table(
            load_table("shipments"),
            [
                "status",
                "shipment_code",
                "shipment_date",
                "delivery_date",
                "customer_name",
                "quantity",
            ],
        )

    elif page == "💰 Costs":
        st.title("Costs & Spending")
        st.caption("Monitor operating costs by category and date.")

        costs_df = load_table("operating_costs")

        if costs_df.empty:
            st.info("No cost records available.")
        else:
            costs_df["amount"] = pd.to_numeric(
                costs_df["amount"],
                errors="coerce",
            ).fillna(0)
            costs_df["cost_date"] = pd.to_datetime(
                costs_df["cost_date"],
                errors="coerce",
            )

            total_cost = costs_df["amount"].sum()
            average_cost = costs_df["amount"].mean()
            largest_category = (
                costs_df
                .groupby("category")["amount"]
                .sum()
                .sort_values(ascending=False)
            )
            top_category = (
                largest_category.index[0]
                if not largest_category.empty
                else "None"
            )

            col1, col2, col3 = st.columns(3)
            col1.metric("Total Operating Cost", f"{total_cost:,.0f}")
            col2.metric("Average Cost Entry", f"{average_cost:,.0f}")
            col3.metric("Highest Cost Category", top_category)

            st.subheader("Cost by Category")
            category_summary = (
                costs_df
                .groupby("category", as_index=False)["amount"]
                .sum()
                .sort_values("amount", ascending=False)
            )
            st.bar_chart(
                category_summary.set_index("category"),
                height=320,
            )

            st.subheader("Cost Records")
            costs_df = costs_df.sort_values(by="amount", ascending=False)
            render_manager_table(
                costs_df,
                ["category", "amount", "cost_date", "description"],
            )

    elif page == "🛡️ Safety & Risk":
        st.title("Safety & Risk")
        st.caption("Prioritize open incidents and serious operational risks.")

        safety_df = load_table("safety_incidents")

        if safety_df.empty:
            st.success("No safety incidents recorded.")
        else:
            safety_df["severity"] = safety_df["severity"].astype(str).str.title()
            safety_df["status"] = safety_df["status"].astype(str).str.title()

            severity_order = {
                "Critical": 0,
                "High": 1,
                "Medium": 2,
                "Low": 3,
            }
            status_order = {
                "Open": 0,
                "Investigating": 1,
                "Resolved": 2,
                "Closed": 3,
            }
            safety_df["_severity_order"] = (
                safety_df["severity"].map(severity_order).fillna(99)
            )
            safety_df["_status_order"] = (
                safety_df["status"].map(status_order).fillna(99)
            )
            safety_df = (
                safety_df
                .sort_values(
                    by=["_status_order", "_severity_order", "incident_date"],
                    ascending=[True, True, False],
                )
                .drop(columns=["_severity_order", "_status_order"])
            )

            open_count = len(safety_df[safety_df["status"] == "Open"])
            serious_count = len(
                safety_df[safety_df["severity"].isin(["Critical", "High"])]
            )

            col1, col2, col3 = st.columns(3)
            col1.metric("Total Incidents", len(safety_df))
            col2.metric("Open Incidents", open_count)
            col3.metric("Critical or High", serious_count)

            st.subheader("Safety Incident Monitor")
            render_manager_table(
                safety_df,
                [
                    "severity",
                    "status",
                    "incident_code",
                    "incident_date",
                    "incident_type",
                    "description",
                ],
            )
except Exception as error:
    st.error(f"Unable to load {page.lower()} data: {error}")
