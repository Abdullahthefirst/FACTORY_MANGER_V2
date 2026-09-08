"""Streamlit application entry point."""

import altair as alt
import pandas as pd
import streamlit as st
from supabase import create_client


st.set_page_config(page_title="FactoryOps", layout="wide")

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
    ]
    return df.drop(columns=hidden_columns, errors="ignore")


try:
    if page == "📊 Overview":
        production_df = load_table("production_records")
        orders_df = load_table("customer_orders")
        inventory_df = load_table("inventory")
        machines_df = load_table("machines")
        alerts_df = load_table("factory_alerts")

        st.title("Factory Manager Dashboard")

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

        st.subheader("Production Performance")

        if not production_df.empty:
            production_df["efficiency"] = (
                production_df["actual_quantity"]
                / production_df["planned_quantity"]
                * 100
            ).round(1)

            st.dataframe(
                manager_view(
                    production_df[
                        [
                            "production_date",
                            "planned_quantity",
                            "actual_quantity",
                            "rejected_quantity",
                            "downtime_minutes",
                            "efficiency",
                        ]
                    ]
                ),
                use_container_width=True,
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
                st.dataframe(manager_view(attention_machines), use_container_width=True)
            else:
                st.success("All machines are operational.")

    elif page == "📦 Orders & Demand":
        st.title("Orders and Demand")
        orders_df = load_table("customer_orders")

        if orders_df.empty:
            st.info("No customer orders available.")
        else:
            st.metric("Total Orders", len(orders_df))
            delayed_orders = orders_df[
                orders_df["status"].str.lower() == "delayed"
            ]
            st.metric("Delayed Orders", len(delayed_orders))
            st.dataframe(manager_view(orders_df), use_container_width=True)

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

            point_count = chart_data["production_date"].nunique()

            if point_count == 1:
                actual_value = chart_data["actual_quantity"].iloc[0]
                planned_value = chart_data["planned_quantity"].iloc[0]
                selected_date = chart_data["production_date"].iloc[0]

                slope_data = pd.DataFrame(
                    {
                        "Stage": [
                            "Origin",
                            "Production",
                            "Origin",
                            "Production",
                        ],
                        "Metric": [
                            "Actual Production",
                            "Actual Production",
                            "Planned Production",
                            "Planned Production",
                        ],
                        "Quantity": [0, actual_value, 0, planned_value],
                    }
                )

                production_chart = (
                    alt.Chart(slope_data)
                    .mark_line(point=True, strokeWidth=4)
                    .encode(
                        x=alt.X(
                            "Stage:N",
                            sort=["Origin", "Production"],
                            title=None,
                        ),
                        y=alt.Y(
                            "Quantity:Q",
                            title="Units",
                            scale=alt.Scale(zero=True),
                        ),
                        color=alt.Color(
                            "Metric:N",
                            scale=alt.Scale(
                                domain=["Actual Production", "Planned Production"],
                                range=["#1769aa", "#8ecae6"],
                            ),
                            title=None,
                        ),
                        tooltip=[
                            alt.Tooltip("Metric:N", title="Metric"),
                            alt.Tooltip(
                                "Quantity:Q",
                                title="Units",
                                format=",.0f",
                            ),
                        ],
                    )
                    .properties(
                        height=360,
                        title=(
                            "Production on "
                            f"{selected_date.strftime('%Y-%m-%d')}"
                        ),
                    )
                )
            else:
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
                            title="Date",
                            axis=alt.Axis(format="%b %d", labelAngle=-45),
                        ),
                        y=alt.Y(
                            "Quantity:Q",
                            title="Units",
                            scale=alt.Scale(zero=True),
                        ),
                        color=alt.Color("Metric:N", title=None),
                        tooltip=[
                            alt.Tooltip(
                                "production_date:T",
                                title="Date",
                                format="%Y-%m-%d",
                            ),
                            alt.Tooltip("Metric:N", title="Metric"),
                            alt.Tooltip(
                                "Quantity:Q",
                                title="Quantity",
                                format=",.0f",
                            ),
                        ],
                    )
                    .properties(height=360, title="Planned vs Actual Production")
                    .interactive()
                )

            st.subheader("Production Performance")
            st.altair_chart(
                production_chart,
                use_container_width=True,
            )

            st.subheader("Production Records")
            st.dataframe(manager_view(filtered_df), use_container_width=True)

    elif page == "📦 Inventory & Supply":
        st.title("Inventory and Supply")
        st.subheader("Inventory")
        st.dataframe(manager_view(load_table("inventory")), use_container_width=True)

        st.subheader("Purchase Orders")
        st.dataframe(
            manager_view(load_table("purchase_orders")),
            use_container_width=True,
        )

    elif page == "⚙️ Machines & Maintenance":
        st.title("Machines and Maintenance")
        st.subheader("Machines")
        st.dataframe(manager_view(load_table("machines")), use_container_width=True)

        st.subheader("Maintenance Records")
        st.dataframe(
            manager_view(load_table("maintenance_records")),
            use_container_width=True,
        )

    elif page == "✅ Quality":
        st.title("Quality Management")
        st.dataframe(
            manager_view(load_table("quality_inspections")),
            use_container_width=True,
        )

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
            st.dataframe(manager_view(employees_df), use_container_width=True)

        st.subheader("Attendance")

        if attendance_df.empty:
            st.info("No attendance records available.")
        else:
            st.dataframe(manager_view(attendance_df), use_container_width=True)

    elif page == "🚚 Logistics":
        st.title("Logistics")
        st.dataframe(manager_view(load_table("shipments")), use_container_width=True)

    elif page == "💰 Costs":
        st.title("Costs and Profitability")
        st.dataframe(
            manager_view(load_table("operating_costs")),
            use_container_width=True,
        )

    elif page == "🛡️ Safety & Risk":
        st.title("Safety and Compliance")
        st.dataframe(
            manager_view(load_table("safety_incidents")),
            use_container_width=True,
        )
except Exception as error:
    st.error(f"Unable to load {page.lower()} data: {error}")
