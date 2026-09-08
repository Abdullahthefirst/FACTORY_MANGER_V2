"""Streamlit application entry point."""

import altair as alt
import pandas as pd
import streamlit as st
from supabase import create_client


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
        "id_material",
        "supplier_id_lookup",
    ]
    return df.drop(columns=hidden_columns, errors="ignore")


def arrange_columns(
    df: pd.DataFrame,
    preferred_columns: list[str],
) -> pd.DataFrame:
    """Move manager decision fields to the start of a dataframe."""
    preferred = [
        column for column in preferred_columns
        if column in df.columns
    ]
    remaining = [
        column for column in df.columns
        if column not in preferred
    ]
    return df[preferred + remaining]


def style_status(value: object) -> str:
    """Apply manager-friendly status colors to dataframe cells."""
    value = str(value).lower()

    if value in [
        "operational",
        "completed",
        "approved",
        "present",
        "received",
        "normal",
        "low",
        "healthy",
    ]:
        return "color: #15803d; font-weight: 600"

    if value in [
        "pending",
        "in progress",
        "ordered",
        "planned",
        "medium",
        "at risk",
    ]:
        return "color: #b45309; font-weight: 600"

    if value in [
        "delayed",
        "open",
        "maintenance",
        "absent",
        "rejected",
        "low stock",
        "attention",
        "high",
        "urgent",
        "critical",
    ]:
        return "color: #dc2626; font-weight: 600"

    return ""


def render_manager_table(
    df: pd.DataFrame,
    preferred_columns: list[str],
) -> None:
    """Render a manager-first table with status-aware styling."""
    display_df = manager_view(df)
    display_df = arrange_columns(display_df, preferred_columns)
    styled_df = display_df.style

    for column in ["status", "priority", "severity", "risk", "stock_status"]:
        if column in display_df.columns:
            styled_df = styled_df.map(style_status, subset=[column])

    st.dataframe(styled_df, use_container_width=True, hide_index=True)


try:
    if page == "📊 Overview":
        production_df = load_table("production_records")
        orders_df = load_table("customer_orders")
        inventory_df = load_table("inventory")
        materials_df = load_table("materials")
        machines_df = load_table("machines")
        safety_df = load_table("safety_incidents")

        st.title("Factory Overview")
        st.caption(
            "A real-time view of production, orders, inventory, machines, "
            "and operational risks."
        )

        total_production = (
            production_df["actual_quantity"].sum()
            if not production_df.empty else 0
        )
        planned_production = (
            production_df["planned_quantity"].sum()
            if not production_df.empty else 0
        )
        rejected_units = (
            production_df["rejected_quantity"].sum()
            if not production_df.empty else 0
        )
        downtime_minutes = (
            production_df["downtime_minutes"].sum()
            if not production_df.empty else 0
        )
        active_orders = (
            len(orders_df[orders_df["status"].isin(["pending", "in production"])])
            if not orders_df.empty else 0
        )
        open_machines = (
            len(machines_df[machines_df["status"] != "operational"])
            if not machines_df.empty else 0
        )

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Actual Production", f"{total_production:,.0f}")
        col2.metric("Planned Production", f"{planned_production:,.0f}")
        col3.metric("Active Orders", active_orders)
        col4.metric("Rejected Units", f"{rejected_units:,.0f}")

        col5, col6 = st.columns(2)
        col5.metric("Downtime", f"{downtime_minutes:,.0f} minutes")
        col6.metric("Machines Requiring Attention", open_machines)

        st.subheader("Attention Required")

        alerts = []

        if not orders_df.empty:
            delayed_orders = orders_df[
                orders_df["status"].astype(str).str.lower() == "delayed"
            ]

            for _, row in delayed_orders.iterrows():
                alerts.append(
                    {
                        "status": "Delayed",
                        "severity": "High",
                        "area": "Orders",
                        "message": (
                            f"{row.get('customer_name', 'Customer')} "
                            "order is delayed"
                        ),
                    }
                )

        if not inventory_df.empty and not materials_df.empty:
            inventory_check = inventory_df.merge(
                materials_df[["id", "name", "reorder_level"]],
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

            low_stock = inventory_check[
                inventory_check["quantity"] <= inventory_check["reorder_level"]
            ]

            for _, row in low_stock.iterrows():
                alerts.append(
                    {
                        "status": "Low Stock",
                        "severity": "High",
                        "area": "Inventory",
                        "message": (
                            f"{row.get('name', 'Material')} "
                            "is below reorder level"
                        ),
                    }
                )

        if not machines_df.empty:
            machines_needing_attention = machines_df[
                machines_df["status"].astype(str).str.lower() != "operational"
            ]

            for _, row in machines_needing_attention.iterrows():
                alerts.append(
                    {
                        "status": "Attention",
                        "severity": "High",
                        "area": "Machines",
                        "message": (
                            f"{row.get('name', 'Machine')} "
                            f"status: {row.get('status', 'Unknown')}"
                        ),
                    }
                )

        if not safety_df.empty:
            open_incidents = safety_df[
                safety_df["status"].astype(str).str.lower() == "open"
            ]

            for _, row in open_incidents.iterrows():
                alerts.append(
                    {
                        "status": "Open",
                        "severity": row.get("severity", "Medium"),
                        "area": "Safety",
                        "message": row.get(
                            "description",
                            "Open safety incident",
                        ),
                    }
                )

        if alerts:
            alerts_display = pd.DataFrame(alerts)
            render_manager_table(
                alerts_display,
                ["status", "severity", "area", "message"],
            )
        else:
            st.success("No urgent operational issues detected.")

        st.subheader("Production Performance")

        if not production_df.empty:
            production_df["efficiency"] = (
                production_df["actual_quantity"]
                / production_df["planned_quantity"]
                * 100
            ).round(1)

            render_manager_table(
                production_df[
                    [
                        "production_date",
                        "planned_quantity",
                        "actual_quantity",
                        "rejected_quantity",
                        "downtime_minutes",
                        "efficiency",
                    ]
                ],
                [
                    "production_date",
                    "planned_quantity",
                    "actual_quantity",
                    "rejected_quantity",
                    "downtime_minutes",
                ],
            )
        else:
            st.info("No production records available.")

        st.subheader("Machines Requiring Attention")

        if not machines_df.empty:
            attention_machines = machines_df[
                machines_df["status"] != "operational"
            ]

            if not attention_machines.empty:
                st.warning("Some machines require attention.")
                render_manager_table(
                    attention_machines,
                    [
                        "status",
                        "machine_code",
                        "name",
                        "last_maintenance_date",
                    ],
                )
            else:
                st.success("All machines are operational.")

    elif page == "📦 Orders & Demand":
        st.title("Orders & Demand")
        st.caption("Monitor delivery commitments and identify orders at risk.")

        orders_df = load_table("customer_orders")

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
                    "due_date",
                    "customer_name",
                    "quantity",
                    "days_remaining",
                ],
            )

    elif page == "🏭 Production":
        st.title("Production Monitoring")
        production_df = load_table("production_records")

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
                    "downtime_reason",
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
                    "expected_date",
                    "ordered_quantity",
                    "received_quantity",
                ],
            )

    elif page == "⚙️ Machines & Maintenance":
        st.title("Machines and Maintenance")
        st.subheader("Machines")
        machines_df = load_table("machines")
        render_manager_table(
            machines_df,
            [
                "status",
                "machine_code",
                "name",
                "last_maintenance_date",
            ],
        )

        st.subheader("Maintenance Records")
        render_manager_table(load_table("maintenance_records"), [])

    elif page == "✅ Quality":
        st.title("Quality Management")
        render_manager_table(load_table("quality_inspections"), [])

    elif page == "👥 Workforce":
        st.title("Workforce Management")

        employees_df = load_table("employees")
        attendance_df = load_table("employee_attendance")

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Employees", len(employees_df))

        if not attendance_df.empty:
            present_count = len(
                attendance_df[attendance_df["status"].str.lower() == "present"]
            )
            absent_count = len(
                attendance_df[attendance_df["status"].str.lower() == "absent"]
            )
        else:
            present_count = 0
            absent_count = 0

        col2.metric("Present Today", present_count)
        col3.metric("Absent Today", absent_count)

        st.subheader("Employees")

        if employees_df.empty:
            st.info("No employees available.")
        else:
            render_manager_table(employees_df, [])

        st.subheader("Attendance")

        if attendance_df.empty:
            st.info("No attendance records available.")
        else:
            render_manager_table(
                attendance_df,
                [
                    "status",
                    "attendance_date",
                    "shift_id",
                    "overtime_hours",
                ],
            )

    elif page == "🚚 Logistics":
        st.title("Logistics")
        render_manager_table(load_table("shipments"), [])

    elif page == "💰 Costs":
        st.title("Costs and Profitability")
        render_manager_table(load_table("operating_costs"), [])

    elif page == "🛡️ Safety & Risk":
        st.title("Safety and Compliance")
        safety_df = load_table("safety_incidents")
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
